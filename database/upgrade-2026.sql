-- Run once on a database created from the original 2024 schema.
-- Phone numbers become text (10-digit mobiles do not fit in INT), and the
-- patient's own phone number gets its own column.

ALTER TABLE `patient_reg`
  MODIFY `FCNo` varchar(20) NOT NULL,
  ADD COLUMN `PatientPhone` varchar(20) DEFAULT NULL AFTER `FCNo`;

ALTER TABLE `iv_details`
  MODIFY `add_info` varchar(255) NOT NULL DEFAULT '';
