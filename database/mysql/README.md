# CineRent MySQL Setup

This folder contains MySQL scripts adding a transaction-aware procedure, a cursor-based procedure, triggers, and functions.

## Prerequisites
- MySQL 8.x (recommended)
- A MySQL user with privileges to create databases, routines, and triggers

## Install
1. Open a MySQL shell and run:

```
mysql -u <USER> -p
```

2. Source the schema and routines:

```
SOURCE database/mysql/schema.sql;
SOURCE database/mysql/routines.sql;
SOURCE database/mysql/triggers.sql;
```

This creates a `cinerent` database with tables `customers`, `movies`, and `rentals`, plus:
- Functions: `fn_seats_available(movie_id)`, `fn_total_revenue(movie_id)`
- Procedure with transaction: `sp_create_rental(customer_id, movie_id, days)`
- Procedure using cursor: `sp_recalc_popularity()`
- Triggers: `tr_movies_no_negative_stock`, `tr_rentals_increment_count`

## Usage Examples
Insert sample rows and test the procedure:

```
USE cinerent;
INSERT INTO customers(name, email) VALUES ('Alice', 'alice@example.com');
INSERT INTO movies(title, stock, price) VALUES ('Inception', 2, 4.99);

-- Create a rental atomically
CALL sp_create_rental(1, 1, 3);

-- Check seats and revenue
SELECT fn_seats_available(1) AS seats_left;
SELECT fn_total_revenue(1) AS total_revenue;

-- Recalculate rentals_count with cursor
CALL sp_recalc_popularity();
```

## Notes
- `sp_create_rental` locks the movie row and uses `START TRANSACTION` / `COMMIT` + `ROLLBACK` and `SIGNAL` for robust error handling.
- Triggers keep `rentals_count` and `last_rented_at` in sync even if inserts bypass the procedure.
- For PostgreSQL or SQLite variants, the syntax and capabilities differ; let me know and I can add equivalents.