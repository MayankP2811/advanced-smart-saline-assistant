-- MySQL / MariaDB schema for the Advanced Smart Saline Assistance System.
-- Contains table definitions only (no patient records).
-- The app can also create these tables itself: `flask --app software/web/app.py init-clinician`.

SET NAMES utf8mb4;

CREATE TABLE `auth` (
  `id` int NOT NULL,
  `name` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `docs` (
  `userid` int NOT NULL AUTO_INCREMENT,
  `name` varchar(80) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`userid`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `patient_reg` (
  `RegID` int NOT NULL AUTO_INCREMENT,
  `Fname` varchar(80) NOT NULL,
  `Lname` varchar(80) NOT NULL,
  `Age` int NOT NULL,
  `Dob` date NOT NULL,
  `Height` int NOT NULL,
  `Weight` int NOT NULL,
  `FCNo` varchar(20) NOT NULL,
  `PatientPhone` varchar(20) DEFAULT NULL,
  `Blood` varchar(10) NOT NULL,
  `Gender` varchar(10) NOT NULL,
  `Handler` varchar(80) NOT NULL,
  `Regtime` datetime(6) NOT NULL DEFAULT current_timestamp(6),
  PRIMARY KEY (`RegID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `iv_details` (
  `therapy_id` int NOT NULL AUTO_INCREMENT,
  `RegID` int NOT NULL,
  `bp` int NOT NULL,
  `sugar` int NOT NULL,
  `pulse` int NOT NULL,
  `iv_type` varchar(255) NOT NULL,
  `drop_factor` int NOT NULL,
  `drop_rate` int NOT NULL,
  `size` int NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `status` varchar(255) NOT NULL DEFAULT 'Inactive',
  `channel` int NOT NULL,
  `add_info` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`therapy_id`),
  KEY `FK_Patient_iv_details` (`RegID`),
  CONSTRAINT `FK_Patient_iv_details` FOREIGN KEY (`RegID`) REFERENCES `patient_reg` (`RegID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
