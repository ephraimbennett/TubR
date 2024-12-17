CREATE TABLE `cards` (
    `card_id` INT AUTO_INCREMENT PRIMARY KEY,
    `list_id` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `position` INT DEFAULT 0, -- For ordering cards within a list
    FOREIGN KEY (list_id) REFERENCES lists(list_id) ON DELETE CASCADE
)