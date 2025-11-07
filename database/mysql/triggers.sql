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

DELIMITER ;