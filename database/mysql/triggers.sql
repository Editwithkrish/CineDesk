-- MySQL triggers for rentals and inventory constraints
USE cinerent;

DELIMITER $$

-- Prevent negative stock values
CREATE TRIGGER tr_movies_no_negative_stock
BEFORE UPDATE ON movies
FOR EACH ROW
BEGIN
  IF NEW.stock < 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock cannot be negative';
  END IF;
END$$

-- Keep rentals_count in sync when a rental is inserted
CREATE TRIGGER tr_rentals_increment_count
AFTER INSERT ON rentals
FOR EACH ROW
BEGIN
  UPDATE movies
     SET rentals_count = rentals_count + 1,
         last_rented_at = NOW()
   WHERE id = NEW.movie_id;
END$$

-- Enforce stock availability when inserting rentals (defense-in-depth)
CREATE TRIGGER tr_rentals_check_stock
BEFORE INSERT ON rentals
FOR EACH ROW
BEGIN
  DECLARE v_stock INT;
  SELECT stock INTO v_stock FROM movies WHERE id = NEW.movie_id;
  IF v_stock IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Movie not found';
  END IF;
  IF v_stock <= 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No stock available';
  END IF;
END$$

-- Restore stock when a rental is marked as returned
CREATE TRIGGER tr_rentals_return_stock
AFTER UPDATE ON rentals
FOR EACH ROW
BEGIN
  IF NEW.rental_status = 'Returned' AND (OLD.rental_status <> 'Returned') THEN
    UPDATE movies
       SET stock = stock + 1,
           availability_status = 'Available'
     WHERE id = NEW.movie_id;
  END IF;
END$$

DELIMITER ;