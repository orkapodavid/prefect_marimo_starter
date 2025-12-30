SELECT CustomerID, CustomerName, Country
FROM Customers
WHERE Country = ?
ORDER BY CustomerName;
