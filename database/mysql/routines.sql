-- MySQL routines: transactions, functions, and cursor-based procedure
USE cinerent;

DELIMITER $$

-- Function: seats available for a movie
CREATE FUNCTION fn_seats_available(p_movie_id INT)
RETURNS INT
DETERMINISTIC
BEGIN
  DECLARE v_stock INT;
  SELECT stock INTO v_stock FROM movies WHERE id = p_movie_id;
  RETURN IFNULL(v_stock, 0);
END$$

-- Function: total revenue for a movie (price * rentals_count)
CREATE FUNCTION fn_total_revenue(p_movie_id INT)
RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
  DECLARE v_price DECIMAL(10,2);
  DECLARE v_count INT;
  SELECT price, rentals_count INTO v_price, v_count FROM movies WHERE id = p_movie_id;
  RETURN IFNULL(v_price, 0.00) * IFNULL(v_count, 0);
END$$

-- Procedure: create a rental with explicit transaction and locking
CREATE PROCEDURE sp_create_rental(
  IN p_customer_id INT,
  IN p_movie_id INT,
  IN p_days INT
)
BEGIN
  DECLARE v_stock INT;

  -- Start transaction and lock the movie row to prevent race conditions
  START TRANSACTION;
  SELECT stock INTO v_stock FROM movies WHERE id = p_movie_id FOR UPDATE;

  IF v_stock IS NULL THEN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Movie not found';
  END IF;

  IF v_stock <= 0 THEN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No stock available';
  END IF;

  INSERT INTO rentals(customer_id, movie_id, days)
  VALUES(p_customer_id, p_movie_id, p_days);

  -- Update inventory; rentals_count will be maintained by trigger
  UPDATE movies
    SET stock = stock - 1,
        last_rented_at = NOW()
    WHERE id = p_movie_id;

  COMMIT;
END$$

-- Procedure: recalculate rentals_count for all movies using a cursor
CREATE PROCEDURE sp_recalc_popularity()
BEGIN
  DECLARE done INT DEFAULT 0;
  DECLARE v_movie_id INT;
  DECLARE cur CURSOR FOR SELECT id FROM movies;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

  OPEN cur;
  read_loop: LOOP
    FETCH cur INTO v_movie_id;
    IF done = 1 THEN
      LEAVE read_loop;
    END IF;

    UPDATE movies m
      SET m.rentals_count = (
        SELECT COUNT(*) FROM rentals r WHERE r.movie_id = v_movie_id
      )
    WHERE m.id = v_movie_id;
  END LOOP;
  CLOSE cur;
END$$

DELIMITER ;