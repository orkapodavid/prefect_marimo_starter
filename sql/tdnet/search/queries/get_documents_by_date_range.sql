-- Get Documents by Date Range
SELECT * FROM tblSearchDocuments
WHERE publish_date BETWEEN :start_date AND :end_date
ORDER BY publish_datetime DESC;
