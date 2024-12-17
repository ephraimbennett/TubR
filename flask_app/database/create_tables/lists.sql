CREATE TABLE `lists` (
    `list_id` INT AUTO_INCREMENT PRIMARY KEY,
    `board_id` INT NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `position` INT DEFAULT 0, -- For ordering lists on the board
    FOREIGN KEY (board_id) REFERENCES boards(board_id) ON DELETE CASCADE
)