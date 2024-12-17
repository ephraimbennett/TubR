CREATE TABLE `board_members` (
    `board_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `role` ENUM('member', 'owner') DEFAULT 'member',
    PRIMARY KEY (board_id, user_id),
    FOREIGN KEY (board_id) REFERENCES boards(board_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
)