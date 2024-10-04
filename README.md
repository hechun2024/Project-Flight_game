*** create database for game, sql query as below:

create database vaccine_game;
use vaccine_game;
source path/to/lp.sql

# drop all tables except airport and country
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE game;
DROP TABLE goal;
DROP TABLE goal_reached;
SET FOREIGN_KEY_CHECKS = 1;

# creat new tables for the game
CREATE TABLE game (
    id INT AUTO_INCREMENT PRIMARY KEY,
    money DECIMAL(10, 2) NOT NULL,
    player_range DECIMAL(10, 2) NOT NULL,
    location VARCHAR(10) NOT NULL,
    screen_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE element (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name CHAR(1) NOT NULL,  -- A, B, C, D
    total_quantity INT NOT NULL  -- A:4, B:3, C:3, D:2
);

INSERT INTO element (name, total_quantity) VALUES
('A', 4),
('B', 3),
('C', 3),
('D', 2)
ON DUPLICATE KEY UPDATE name = VALUES(name), total_quantity = VALUES(total_quantity);

CREATE TABLE port_contents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  game_id INT NOT NULL,
  airport VARCHAR(10) NOT NULL,
  content_type ENUM('element', 'lucky_box') NOT NULL,
  content_value CHAR(1) DEFAULT NULL,
  found TINYINT(1) DEFAULT 0
 );

