-- Run in your own database. Rename username_ to your assigned username if required.
CREATE TABLE IF NOT EXISTS `username_auth` (
  `token` VARCHAR(64) NOT NULL PRIMARY KEY
);
INSERT INTO `username_auth` (`token`) VALUES ('123')
ON DUPLICATE KEY UPDATE `token` = VALUES(`token`);

CREATE TABLE IF NOT EXISTS `username_api_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `endpoint` VARCHAR(80) NOT NULL,
  `token` VARCHAR(64) NULL,
  `response` VARCHAR(10) NOT NULL,
  `dt` DATETIME NOT NULL
);
-- class_datapoints is already supplied by the instructor; do not recreate it.
