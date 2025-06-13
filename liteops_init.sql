/*
 Navicat Premium Data Transfer

 Source Server         : 127.0.0.1
 Source Server Type    : MySQL
 Source Server Version : 80100 (8.1.0)
 Source Host           : 127.0.0.1:3306
 Source Schema         : liteops

 Target Server Type    : MySQL
 Target Server Version : 80100 (8.1.0)
 File Encoding         : 65001

 Date: 12/06/2025 17:13:48
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
-- ----------------------------
-- Table structure for build_history
-- ----------------------------
DROP TABLE IF EXISTS `build_history`;
CREATE TABLE `build_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `history_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `build_number` int NOT NULL,
  `branch` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `commit_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `version` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `requirement` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `build_log` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `stages` json NOT NULL,
  `build_time` json NOT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `operator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `task_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `history_id` (`history_id`),
  UNIQUE KEY `build_history_task_id_build_number_8fc0b316_uniq` (`task_id`,`build_number`),
  KEY `build_history_operator_id_f43bdff4_fk_user_user_id` (`operator_id`),
  CONSTRAINT `build_history_operator_id_f43bdff4_fk_user_user_id` FOREIGN KEY (`operator_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `build_history_task_id_dfb7725d_fk_build_task_task_id` FOREIGN KEY (`task_id`) REFERENCES `build_task` (`task_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for build_task
-- ----------------------------
DROP TABLE IF EXISTS `build_task`;
CREATE TABLE `build_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `branch` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `stages` json NOT NULL,
  `notification_channels` json NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `last_build_number` int NOT NULL,
  `total_builds` int NOT NULL,
  `success_builds` int NOT NULL,
  `failure_builds` int NOT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `environment_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `git_token_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `project_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `version` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `build_time` json NOT NULL DEFAULT (_utf8mb3'{}'),
  `requirement` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `building_status` varchar(20) COLLATE utf8mb4_bin DEFAULT NULL,
  `external_script_config` json NOT NULL DEFAULT (_utf8mb3'{}'),
  `use_external_script` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `task_id` (`task_id`),
  KEY `build_task_creator_id_e702c745_fk_user_user_id` (`creator_id`),
  KEY `build_task_environment_id_8f5e7798_fk_environment_environment_id` (`environment_id`),
  KEY `build_task_git_token_id_813ab2b1_fk_gitlab_to` (`git_token_id`),
  KEY `build_task_project_id_f92c80ac_fk_project_project_id` (`project_id`),
  CONSTRAINT `build_task_creator_id_e702c745_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `build_task_environment_id_8f5e7798_fk_environment_environment_id` FOREIGN KEY (`environment_id`) REFERENCES `environment` (`environment_id`),
  CONSTRAINT `build_task_git_token_id_813ab2b1_fk_gitlab_to` FOREIGN KEY (`git_token_id`) REFERENCES `gitlab_token_credential` (`credential_id`),
  CONSTRAINT `build_task_project_id_f92c80ac_fk_project_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for environment
-- ----------------------------
DROP TABLE IF EXISTS `environment`;
CREATE TABLE `environment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `environment_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `environment_id` (`environment_id`),
  KEY `environment_creator_id_2f30820a_fk_user_user_id` (`creator_id`),
  CONSTRAINT `environment_creator_id_2f30820a_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for gitlab_token_credential
-- ----------------------------
DROP TABLE IF EXISTS `gitlab_token_credential`;
CREATE TABLE `gitlab_token_credential` (
  `id` int NOT NULL AUTO_INCREMENT,
  `credential_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `credential_id` (`credential_id`),
  KEY `gitlab_token_credential_creator_id_d53c3666_fk_user_user_id` (`creator_id`),
  CONSTRAINT `gitlab_token_credential_creator_id_d53c3666_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for kubeconfig_credential
-- ----------------------------
DROP TABLE IF EXISTS `kubeconfig_credential`;
CREATE TABLE `kubeconfig_credential` (
  `id` int NOT NULL AUTO_INCREMENT,
  `credential_id` varchar(32) COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) COLLATE utf8mb4_bin DEFAULT NULL,
  `description` longtext COLLATE utf8mb4_bin,
  `kubeconfig_content` longtext COLLATE utf8mb4_bin,
  `cluster_name` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL,
  `context_name` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `credential_id` (`credential_id`),
  KEY `kubeconfig_credential_creator_id_a3490ac1_fk_user_user_id` (`creator_id`),
  CONSTRAINT `kubeconfig_credential_creator_id_a3490ac1_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for login_attempt
-- ----------------------------
DROP TABLE IF EXISTS `login_attempt`;
CREATE TABLE `login_attempt` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ip_address` varchar(50) COLLATE utf8mb4_bin DEFAULT NULL,
  `failed_attempts` int NOT NULL,
  `locked_until` datetime(6) DEFAULT NULL,
  `last_attempt_time` datetime(6) NOT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `user_id` varchar(32) COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `login_attempt_user_id_ip_address_a69098a0_uniq` (`user_id`,`ip_address`),
  CONSTRAINT `login_attempt_user_id_0f42fcb7_fk_user_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for login_log
-- ----------------------------
DROP TABLE IF EXISTS `login_log`;
CREATE TABLE `login_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `log_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `ip_address` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `user_agent` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `fail_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `login_time` datetime(6) DEFAULT NULL,
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `log_id` (`log_id`),
  KEY `login_log_user_id_69642132_fk_user_user_id` (`user_id`),
  CONSTRAINT `login_log_user_id_69642132_fk_user_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for notification_robot
-- ----------------------------
DROP TABLE IF EXISTS `notification_robot`;
CREATE TABLE `notification_robot` (
  `id` int NOT NULL AUTO_INCREMENT,
  `robot_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `webhook` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `secret` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `remark` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `ip_list` json DEFAULT NULL,
  `keywords` json DEFAULT NULL,
  `security_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `robot_id` (`robot_id`),
  KEY `notification_robot_creator_id_de406276_fk_user_user_id` (`creator_id`),
  CONSTRAINT `notification_robot_creator_id_de406276_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for project
-- ----------------------------
DROP TABLE IF EXISTS `project`;
CREATE TABLE `project` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `category` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `repository` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `project_id` (`project_id`),
  KEY `project_creator_id_e70918ae_fk_user_user_id` (`creator_id`),
  CONSTRAINT `project_creator_id_e70918ae_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for role
-- ----------------------------
DROP TABLE IF EXISTS `role`;
CREATE TABLE `role` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `permissions` json DEFAULT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `role_id` (`role_id`),
  UNIQUE KEY `name` (`name`),
  KEY `role_creator_id_37780e7e_fk_user_user_id` (`creator_id`),
  CONSTRAINT `role_creator_id_37780e7e_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for security_config
-- ----------------------------
DROP TABLE IF EXISTS `security_config`;
CREATE TABLE `security_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `min_password_length` int NOT NULL,
  `password_complexity` json NOT NULL,
  `session_timeout` int NOT NULL,
  `max_login_attempts` int NOT NULL,
  `lockout_duration` int NOT NULL,
  `enable_2fa` tinyint(1) NOT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for ssh_key_credential
-- ----------------------------
DROP TABLE IF EXISTS `ssh_key_credential`;
CREATE TABLE `ssh_key_credential` (
  `id` int NOT NULL AUTO_INCREMENT,
  `credential_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `private_key` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin,
  `passphrase` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `creator_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `credential_id` (`credential_id`),
  KEY `ssh_key_credential_creator_id_c7396682_fk_user_user_id` (`creator_id`),
  CONSTRAINT `ssh_key_credential_creator_id_c7396682_fk_user_user_id` FOREIGN KEY (`creator_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `password` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `status` smallint DEFAULT NULL,
  `login_time` datetime(6) DEFAULT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for user_role
-- ----------------------------
DROP TABLE IF EXISTS `user_role`;
CREATE TABLE `user_role` (
  `id` int NOT NULL AUTO_INCREMENT,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `role_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_role_user_id_role_id_a1d0951e_uniq` (`user_id`,`role_id`),
  KEY `user_role_role_id_6a11361a_fk_role_role_id` (`role_id`),
  CONSTRAINT `user_role_role_id_6a11361a_fk_role_role_id` FOREIGN KEY (`role_id`) REFERENCES `role` (`role_id`),
  CONSTRAINT `user_role_user_id_12d84374_fk_user_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for user_token
-- ----------------------------
DROP TABLE IF EXISTS `user_token`;
CREATE TABLE `user_token` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `token` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `user_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_id` (`token_id`),
  KEY `user_token_user_id_69e1f632_fk_user_user_id` (`user_id`),
  CONSTRAINT `user_token_user_id_69e1f632_fk_user_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- 初始化数据
-- ----------------------------

-- 插入用户数据
INSERT INTO `user` (`id`, `user_id`, `username`, `name`, `password`, `email`, `status`, `login_time`, `create_time`, `update_time`) VALUES (1, '9bfef5a1ee1d4054be9727934ad112es', 'admin', '管理员', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin@example.com', 1, '2025-06-12 16:29:01.815564', '2025-03-26 11:41:20.549327', '2025-06-12 16:29:01.815655');

-- 插入角色数据
INSERT INTO `role` (`id`, `role_id`, `name`, `description`, `permissions`, `create_time`, `update_time`, `creator_id`) VALUES (1, '333ec25423e04a4e96b4bb238de51cc3', '管理员', '系统管理员，拥有所有权限', '{\"data\": {\"operations\": [\"view\"], \"project_ids\": [], \"project_scope\": \"all\", \"environment_scope\": \"all\", \"environment_types\": []}, \"menu\": [\"/projects\", \"/projects/list\", \"/build\", \"/build/tasks\", \"/build/history\", \"/logs/login\", \"/user\", \"/user/list\", \"/user/role\", \"/credentials\", \"/environments\", \"/environments/list\", \"/dashboard\", \"/logs\", \"/system/basic\", \"/system/notification\", \"/system/backup\", \"/system\"], \"function\": {\"role\": [\"view\", \"create\", \"edit\", \"delete\", \"assign_permission\"], \"user\": [\"view\", \"create\", \"edit\", \"delete\", \"toggle_status\", \"reset_password\"], \"build\": [\"view\", \"create\", \"edit\", \"delete\", \"execute\", \"view_log\"], \"project\": [\"view\", \"create\", \"edit\", \"delete\"], \"release\": [\"view\", \"create\", \"edit\", \"delete\", \"approve\", \"execute\", \"rollback\"], \"build_task\": [\"view\", \"create\", \"edit\", \"delete\", \"execute\", \"view_log\", \"disable\"], \"credential\": [\"view\", \"create\", \"edit\", \"delete\"], \"logs_login\": [\"view\"], \"environment\": [\"view\", \"create\", \"edit\", \"delete\"], \"notification\": [\"view\", \"create\", \"edit\", \"delete\", \"test\"], \"system_basic\": [\"view\", \"edit\", \"create\", \"delete\", \"test\"], \"build_history\": [\"view\", \"view_log\", \"rollback\"], \"build_approval\": [\"view\", \"request\", \"approve\"], \"logs_operation\": [\"view\"]}}', '2025-03-27 14:45:04.779759', '2025-06-09 16:04:40.782374', '9bfef5a1ee1d4054be9727934ad112es');
INSERT INTO `role` (`id`, `role_id`, `name`, `description`, `permissions`, `create_time`, `update_time`, `creator_id`) VALUES (2, '5575cfdc75dd4f8e9c5441359478314e', '开发人员', '开发人员，负责编写代码和构建', '{\"data\": {\"operations\": [\"view\"], \"project_ids\": [], \"project_scope\": \"custom\", \"environment_scope\": \"custom\", \"environment_types\": []}, \"menu\": [], \"function\": {\"build\": [], \"project\": [], \"release\": [\"view\", \"create\", \"edit\"], \"build_task\": [], \"credential\": [], \"environment\": [], \"notification\": [], \"build_history\": []}}', '2025-03-27 14:45:04.783696', '2025-04-17 09:42:38.079772', '9bfef5a1ee1d4054be9727934ad112es');
INSERT INTO `role` (`id`, `role_id`, `name`, `description`, `permissions`, `create_time`, `update_time`, `creator_id`) VALUES (3, 'ea78a0379d7d45559c4db69e38f07cd3', '测试人员', '测试人员，负责测试和验证', '{\"data\": {\"operations\": [\"view\"], \"project_ids\": [], \"project_scope\": \"custom\", \"environment_scope\": \"custom\", \"environment_types\": []}, \"menu\": [], \"function\": {\"build\": [\"view\", \"view_log\"], \"project\": [], \"release\": [\"view\", \"approve\"], \"build_history\": []}}', '2025-03-27 14:45:04.785872', '2025-04-17 09:43:16.944919', '9bfef5a1ee1d4054be9727934ad112es');
INSERT INTO `role` (`id`, `role_id`, `name`, `description`, `permissions`, `create_time`, `update_time`, `creator_id`) VALUES (4, '3aac992b37e441abbeb2c67a0c79f01f', '运维人员', '运维人员，负责部署和运维', '{\"data\": {\"operations\": [\"view\"], \"project_ids\": [], \"project_scope\": \"custom\", \"environment_scope\": \"custom\", \"environment_types\": []}, \"menu\": [], \"function\": {\"build\": [\"view\", \"execute\", \"view_log\"], \"project\": [], \"release\": [\"view\", \"approve\", \"execute\", \"rollback\"], \"environment\": [], \"notification\": [], \"build_history\": []}}', '2025-03-27 14:45:04.787850', '2025-04-17 09:44:08.530007', '9bfef5a1ee1d4054be9727934ad112es');

-- 插入用户角色关联数据
INSERT INTO `user_role` (`id`, `create_time`, `update_time`, `role_id`, `user_id`) VALUES (1, '2025-03-27 14:45:11.269249', '2025-03-27 14:45:11.269261', '333ec25423e04a4e96b4bb238de51cc3', '9bfef5a1ee1d4054be9727934ad112es');

SET FOREIGN_KEY_CHECKS = 1;
