-- The product catalog of the inventory system, with its constraints.
CREATE TABLE Suppliers (
    ID INT PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    ContactName VARCHAR(255),
    ContactPhone VARCHAR(20)
);

CREATE TABLE Products (
    ID INT PRIMARY KEY,
    GTIN VARCHAR(13) NOT NULL UNIQUE CHECK (length(GTIN) = 13),
    Name VARCHAR(255) NOT NULL,
    Category VARCHAR(50),
    UnitPrice DECIMAL(10, 2) NOT NULL CHECK (UnitPrice > 0),
    QuantityInStock INT NOT NULL CHECK (QuantityInStock >= 0),
    Unit VARCHAR(5) NOT NULL CHECK (Unit IN ('count', 'kg', 'liter')),
    SupplierID INT,
    CHECK (Category <> 'produce' OR Unit IN ('count', 'kg')),
    FOREIGN KEY (SupplierID) REFERENCES Suppliers(ID)
);

CREATE TABLE Deliveries (
    ID INT PRIMARY KEY,
    ProductID INT NOT NULL REFERENCES Products(ID),
    DeliveryDate DATE NOT NULL,
    BestBefore DATE NOT NULL,
    Quantity DECIMAL(10, 3) NOT NULL CHECK (Quantity > 0),
    CHECK (BestBefore > DeliveryDate)
);
