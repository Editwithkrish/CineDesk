-- MySQL schema for CineRent demo
CREATE DATABASE IF NOT EXISTS cinerent;
USE cinerent;

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  phone VARCHAR(20),
  address VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Movies inventory
CREATE TABLE IF NOT EXISTS movies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  stock INT NOT NULL DEFAULT 0,
  price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  rentals_count INT NOT NULL DEFAULT 0,
  last_rented_at DATETIME NULL
);

-- Rentals
CREATE TABLE IF NOT EXISTS rentals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  movie_id INT NOT NULL,
  rented_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  days INT NOT NULL,
  CONSTRAINT fk_rentals_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
  CONSTRAINT fk_rentals_movie FOREIGN KEY (movie_id) REFERENCES movies(id)
);