CREATE TABLE IF NOT EXISTS `boards` (
    `board_id`      int(11)         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name`          varchar(255)    NOT NULL,
    `description`   varchar(511)    DEFAULT ' ',
    `owner_id`      int(11)         NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE 
)