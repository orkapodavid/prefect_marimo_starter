# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair==5.5.0",
#     "marimo",
#     "polars==1.34.0",
#     "prefect==3.4.25",
#     "pytest==8.4.2",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(
    width="medium",
    auto_download=["html"],
    sql_output="polars",
)

with app.setup:
    from prefect import task, flow
    import polars as pl
    import time


@app.function
@task
def read_data(limit=None):
    df = pl.scan_parquet(
        "https://github.com/koaning/wow-avatar-datasets/raw/refs/heads/main/wow-full.parquet"
    )
    if limit:
        return df.tail(limit).collect()
    return df.collect()


@app.function
@task
def set_types(dataf):
    return dataf.with_columns(
        [pl.col("guild").is_not_null(), pl.col("datetime").cast(pl.Int64).alias("timestamp")]
    )


@app.function
@task
def clean_data(dataf):
    return dataf.filter(
        ~pl.col("class").is_in(["482", "Death Knight", "3485伊", "2400"]),
        pl.col("race").is_in(["Troll", "Orc", "Undead", "Tauren", "Blood Elf"]),
    )


@app.function
@task
def sessionize(dataf, threshold=20 * 60 * 1000):
    return (
        dataf.sort(["player_id", "timestamp"])
        .with_columns(
            (pl.col("timestamp").diff().cast(pl.Int64) > threshold)
            .fill_null(True)
            .alias("ts_diff"),
            (pl.col("player_id").diff() != 0).fill_null(True).alias("char_diff"),
        )
        .with_columns((pl.col("ts_diff") | pl.col("char_diff")).alias("new_session_mark"))
        .with_columns(pl.col("new_session_mark").cum_sum().alias("session"))
        .drop(["char_diff", "ts_diff", "new_session_mark"])
    )


@app.function
@task
def add_features(dataf):
    return dataf.with_columns(
        pl.col("player_id").count().over("session").alias("session_length"),
        pl.col("session").n_unique().over("player_id").alias("n_sessions_per_char"),
    )


@app.cell
def _():
    def test_demo():
        assert True

    def test_also_demo():
        assert True
    return


@app.function
@task
def remove_bots(dataf, max_session_hours=24):
    # We're using some domain knowledge. The logger of our dataset should log
    # data every 10 minutes. That's what this line is based on.
    n_rows = max_session_hours * 6
    return dataf.filter(pl.col("session_length").max().over("player_id") < n_rows)


@app.function
@task
def pretend_to_write_to_db(dataf):
    time.sleep(2)


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(cached, df, max_session_threshold, mo):
    @mo.cache
    def plot_per_date(threshold):
        df_out = cached.pipe(remove_bots, max_session_hours=max_session_threshold.value)
        agg_orig = (
            df.with_columns(date=pl.col("datetime").dt.date())
            .group_by("date")
            .len()
            .with_columns(set=pl.lit("original"))
        )
        agg_clean = (
            df_out.with_columns(date=pl.col("datetime").dt.date())
            .group_by("date")
            .len()
            .with_columns(set=pl.lit("clean"))
        )
        return (
            pl.concat([agg_orig, agg_clean])
            .plot.line(x="date", y="len", color="set")
            .properties(width=600)
        )
    return (plot_per_date,)


@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        df = read_data()

        cached = (
            df.pipe(set_types)
            .pipe(clean_data)
            .pipe(sessionize, threshold=30 * 60 * 1000)
            .pipe(add_features)
        )
    return cached, df


@app.cell
def _(max_session_threshold, mo, plot_per_date):
    if mo.app_meta().mode == "edit":
        chart = plot_per_date(max_session_threshold.value)
    return (chart,)


@app.cell
def _(mo):
    if mo.app_meta().mode == "edit":
        max_session_threshold = mo.ui.slider(2, 24, 1, value=24, label="Max session length (hours)")
    return (max_session_threshold,)


@app.cell
def _(chart, max_session_threshold, mo):
    out = None 
    if mo.app_meta().mode == "edit":
        out = mo.vstack([max_session_threshold, chart])
    out
    return


@app.function
@flow
def run_pipeline():
    cached = (
        read_data()
        .pipe(set_types)
        .pipe(clean_data)
        .pipe(sessionize, threshold=30 * 60 * 1000)
        .pipe(add_features)
    )
    cached.pipe(pretend_to_write_to_db)
    cached.pipe(remove_bots).pipe(pretend_to_write_to_db)


@app.cell
def _(mo):
    if mo.app_meta().mode == "script":
        run_pipeline()
    return


if __name__ == "__main__":
    app.run()
