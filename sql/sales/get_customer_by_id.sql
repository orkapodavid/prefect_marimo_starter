---
description: "Retrieves a customer record by their unique ID."
parameters:
  - name: "customer_id"
    type: "int"
---
SELECT
    CustomerID,
    CustomerName,
    ContactName,
    Country
FROM
    Customers
WHERE
    CustomerID = ?;
