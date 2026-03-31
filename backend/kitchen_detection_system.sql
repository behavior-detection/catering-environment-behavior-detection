-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: localhost    Database: kitchen_detection_system
-- ------------------------------------------------------
-- Server version	8.0.41

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `access_logs`
--

DROP TABLE IF EXISTS `access_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `access_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token_id` int NOT NULL,
  `visitor_ip` varchar(45) DEFAULT NULL,
  `visitor_user_id` int DEFAULT NULL,
  `access_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `action` enum('view_list','play_video','download') NOT NULL,
  `video_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `visitor_user_id` (`visitor_user_id`),
  KEY `video_id` (`video_id`),
  KEY `idx_token_id` (`token_id`),
  KEY `idx_access_time` (`access_time`),
  CONSTRAINT `access_logs_ibfk_1` FOREIGN KEY (`token_id`) REFERENCES `share_tokens` (`id`),
  CONSTRAINT `access_logs_ibfk_2` FOREIGN KEY (`visitor_user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `access_logs_ibfk_3` FOREIGN KEY (`video_id`) REFERENCES `videos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `access_logs`
--

LOCK TABLES `access_logs` WRITE;
/*!40000 ALTER TABLE `access_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `access_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `admin`
--

DROP TABLE IF EXISTS `admin`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Name` varchar(100) DEFAULT NULL,
  `Password` varchar(100) DEFAULT NULL,
  `AdminID` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin`
--

LOCK TABLES `admin` WRITE;
/*!40000 ALTER TABLE `admin` DISABLE KEYS */;
INSERT INTO `admin` VALUES (1,'孙晓军','Sun@Admin999','ADM20240001'),(2,'周雨萱','Zhou#Root888','ADM20240002'),(3,'吴俊杰','Wu$Super777','ADM20240003');
/*!40000 ALTER TABLE `admin` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ai_analysis_reports`
--

DROP TABLE IF EXISTS `ai_analysis_reports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_analysis_reports` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `analysis_id` varchar(100) NOT NULL,
  `analysis_type` varchar(50) NOT NULL,
  `risk_level` varchar(20) NOT NULL,
  `analysis_result` json NOT NULL,
  `summary` longtext NOT NULL,
  `recommendations` json NOT NULL,
  `compliance_score` int NOT NULL,
  `confidence_score` decimal(3,2) NOT NULL,
  `processing_time` datetime(6) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `violation_record_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `analysis_id` (`analysis_id`),
  KEY `ai_analysis_reports_violation_record_id_1589e9e7_fk_violation` (`violation_record_id`),
  KEY `ai_analysis_analysi_101b08_idx` (`analysis_id`),
  KEY `ai_analysis_risk_le_d6e7a4_idx` (`risk_level`),
  KEY `ai_analysis_created_2f798d_idx` (`created_at`),
  CONSTRAINT `ai_analysis_reports_violation_record_id_1589e9e7_fk_violation` FOREIGN KEY (`violation_record_id`) REFERENCES `violations_records` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ai_analysis_reports`
--

LOCK TABLES `ai_analysis_reports` WRITE;
/*!40000 ALTER TABLE `ai_analysis_reports` DISABLE KEYS */;
/*!40000 ALTER TABLE `ai_analysis_reports` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ai_query_history`
--

DROP TABLE IF EXISTS `ai_query_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_query_history` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `query` longtext NOT NULL,
  `time_range_hours` int NOT NULL,
  `query_all_data` tinyint(1) NOT NULL,
  `response_data` json NOT NULL,
  `success` tinyint(1) NOT NULL,
  `error_message` longtext NOT NULL,
  `processing_time` double NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ai_query_history_user_id_082cfbd7_fk_auth_user_id` (`user_id`),
  CONSTRAINT `ai_query_history_user_id_082cfbd7_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ai_query_history`
--

LOCK TABLES `ai_query_history` WRITE;
/*!40000 ALTER TABLE `ai_query_history` DISABLE KEYS */;
INSERT INTO `ai_query_history` VALUES (1,'哪个摄像头违规最多？',24,0,'{}',0,'AI服务不可用: HTTPConnectionPool(host=\'localhost\', port=5001): Max retries exceeded with url: /api/query (Caused by NewConnectionError(\'<urllib3.connection.HTTPConnection object at 0x0000024A2B8DC860>: Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。\'))',4.1345391273498535,'2025-09-22 11:04:00.233979',NULL),(2,'今天违规情况如何？',24,0,'{}',0,'AI服务不可用: HTTPConnectionPool(host=\'localhost\', port=5001): Max retries exceeded with url: /api/query (Caused by NewConnectionError(\'<urllib3.connection.HTTPConnection object at 0x000002100D4AC080>: Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。\'))',4.103022813796997,'2025-09-22 11:23:08.706512',NULL),(3,'今天违规情况如何？',24,0,'{}',0,'AI服务不可用: HTTPConnectionPool(host=\'localhost\', port=5001): Max retries exceeded with url: /api/query (Caused by NewConnectionError(\'<urllib3.connection.HTTPConnection object at 0x0000019A6DF295B0>: Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。\'))',4.088416337966919,'2025-09-22 11:54:43.738452',NULL),(4,'哪个摄像头违规最多？',24,0,'{}',0,'AI服务不可用: HTTPConnectionPool(host=\'localhost\', port=5001): Max retries exceeded with url: /api/query (Caused by NewConnectionError(\'<urllib3.connection.HTTPConnection object at 0x0000019A6DF285F0>: Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。\'))',4.0988781452178955,'2025-09-22 11:55:24.474011',NULL),(5,'哪个摄像头违规最多？',24,0,'{}',0,'AI服务不可用: HTTPConnectionPool(host=\'localhost\', port=5001): Max retries exceeded with url: /api/query (Caused by NewConnectionError(\'<urllib3.connection.HTTPConnection object at 0x0000019A6DF28530>: Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。\'))',4.085022211074829,'2025-09-22 11:57:55.569416',NULL),(6,'哪个摄像头违规最多？',24,0,'{\"query\": \"哪个摄像头违规最多？\", \"success\": true, \"analysis\": {\"suggestions\": [\"继续保持现有管理标准\", \"定期检查检测系统运行状态\", \"保持员工培训和安全意识教育\", \"建立预防性管理机制\"], \"direct_answer\": \"在指定时间范围内没有检测到违规数据。\", \"detailed_explanation\": \"系统在指定时间范围内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。\"}, \"query_info\": {\"query_all_data\": false, \"analysis_method\": \"smart_time_range_engine\", \"adjustment_reason\": \"\", \"time_range_adjusted\": false, \"user_selected_hours\": 24, \"smart_detected_hours\": 24, \"janus_model_available\": false}, \"data_summary\": {}}',1,'',2.1688098907470703,'2025-09-22 11:59:39.667997',NULL),(7,'哪个摄像头违规最多？',24,0,'{\"query\": \"哪个摄像头违规最多？\", \"success\": true, \"analysis\": {\"suggestions\": [\"继续保持现有管理标准\", \"定期检查检测系统运行状态\", \"保持员工培训和安全意识教育\", \"建立预防性管理机制\"], \"direct_answer\": \"在指定时间范围内没有检测到违规数据。\", \"detailed_explanation\": \"系统在指定时间范围内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。\"}, \"query_info\": {\"query_all_data\": false, \"analysis_method\": \"smart_time_range_engine\", \"adjustment_reason\": \"\", \"time_range_adjusted\": false, \"user_selected_hours\": 24, \"smart_detected_hours\": 24, \"janus_model_available\": false}, \"data_summary\": {}}',1,'',2.0335614681243896,'2025-09-22 11:59:41.743286',NULL),(8,'口罩佩戴情况怎么样？',24,0,'{}',0,'AI服务不可用: HTTPConnectionPool(host=\'localhost\', port=5001): Read timed out. (read timeout=60)',62.048928022384644,'2025-09-22 12:00:48.811519',NULL),(9,'今天违规情况如何？',24,0,'{\"query\": \"今天违规情况如何？\", \"success\": true, \"analysis\": {\"suggestions\": [\"继续保持现有管理标准\", \"定期检查检测系统运行状态\", \"保持员工培训和安全意识教育\", \"建立预防性管理机制\"], \"direct_answer\": \"在指定时间范围内没有检测到违规数据。\", \"detailed_explanation\": \"系统在指定时间范围内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。\"}, \"query_info\": {\"query_all_data\": false, \"analysis_method\": \"smart_time_range_engine\", \"adjustment_reason\": \"检测到\'今天\'关键词\", \"time_range_adjusted\": true, \"user_selected_hours\": 24, \"smart_detected_hours\": 24, \"janus_model_available\": false}, \"data_summary\": {}}',1,'',2.149329662322998,'2025-09-28 08:15:39.833414',NULL),(10,'今天违规情况如何？',24,0,'{\"query\": \"今天违规情况如何？\", \"success\": true, \"analysis\": {\"suggestions\": [\"继续保持现有管理标准\", \"定期检查检测系统运行状态\", \"保持员工培训和安全意识教育\", \"建立预防性管理机制\"], \"direct_answer\": \"在指定时间范围内没有检测到违规数据。\", \"detailed_explanation\": \"系统在指定时间范围内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。\"}, \"query_info\": {\"query_all_data\": false, \"analysis_method\": \"smart_time_range_engine\", \"adjustment_reason\": \"检测到\'今天\'关键词\", \"time_range_adjusted\": true, \"user_selected_hours\": 24, \"smart_detected_hours\": 24, \"janus_model_available\": false}, \"data_summary\": {}}',1,'',2.045727014541626,'2025-09-28 08:15:41.904681',NULL),(11,'哪个摄像头违规最多？',24,0,'{\"query\": \"哪个摄像头违规最多？\", \"success\": true, \"analysis\": {\"summary\": {\"total_records\": 0, \"active_cameras\": 0, \"time_description\": \"最近24小时\", \"total_violations\": 0}, \"suggestions\": [\"继续保持现有管理标准\", \"定期检查检测系统运行状态\", \"保持员工培训和安全意识教育\", \"建立预防性管理机制\"], \"direct_answer\": \"在指定时间范围内没有检测到违规数据。\", \"recent_records\": [], \"violations_by_date\": {}, \"violations_by_hour\": {}, \"violations_by_type\": {}, \"detailed_explanation\": \"系统在指定时间范围内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。\", \"violations_by_camera\": {}}, \"query_info\": {\"query_all_data\": false, \"analysis_method\": \"smart_time_range_engine\", \"adjustment_reason\": \"\", \"time_range_adjusted\": false, \"user_selected_hours\": 24, \"smart_detected_hours\": 24, \"janus_model_available\": false}, \"data_summary\": {\"eid\": \"914403007MA1234567X\", \"data_source\": \"ai_service_with_files\", \"file_records_count\": 0, \"enhanced_with_cache\": true, \"file_total_violations\": 0}, \"query_timestamp\": \"2025-09-28T10:41:22.576544+00:00\", \"processing_time_seconds\": 137.09}',1,'',137.09359908103943,'2025-09-28 10:41:22.576544',NULL),(12,'哪个摄像头违规最多？',24,0,'{\"query\": \"哪个摄像头违规最多？\", \"success\": true, \"analysis\": {\"suggestions\": [\"继续保持现有管理标准\", \"定期检查检测系统运行状态\", \"保持员工培训和安全意识教育\", \"建立预防性管理机制\"], \"direct_answer\": \"在指定时间范围内没有检测到违规数据。\", \"detailed_explanation\": \"系统在指定时间范围内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。\"}, \"query_info\": {\"query_all_data\": false, \"analysis_method\": \"smart_time_range_engine\", \"adjustment_reason\": \"\", \"time_range_adjusted\": false, \"user_selected_hours\": 24, \"smart_detected_hours\": 24, \"janus_model_available\": false}, \"data_summary\": {}, \"query_timestamp\": \"2025-10-03T07:45:20.052714+00:00\", \"processing_time_seconds\": 2.11}',1,'',2.1059343814849854,'2025-10-03 07:45:20.052714',NULL),(13,'哪个摄像头违规最多？',24,0,'{\"query\": \"哪个摄像头违规最多？\", \"success\": true, \"analysis\": {\"summary\": {\"total_records\": 0, \"active_cameras\": 0, \"time_description\": \"最近24小时\", \"total_violations\": 0}, \"suggestions\": [\"继续保持现有管理标准\", \"定期检查检测系统运行状态\", \"保持员工培训和安全意识教育\", \"建立预防性管理机制\"], \"direct_answer\": \"在指定时间范围内没有检测到违规数据。\", \"recent_records\": [], \"violations_by_date\": {}, \"violations_by_hour\": {}, \"violations_by_type\": {}, \"detailed_explanation\": \"系统在指定时间范围内未发现任何违规行为，表明当前管理状况良好。建议继续保持现有管理标准，定期检查系统运行状态。\", \"violations_by_camera\": {}}, \"query_info\": {\"query_all_data\": false, \"analysis_method\": \"smart_time_range_engine\", \"adjustment_reason\": \"\", \"time_range_adjusted\": false, \"user_selected_hours\": 24, \"smart_detected_hours\": 24, \"janus_model_available\": false}, \"data_summary\": {\"eid\": \"371400228016303\", \"data_source\": \"ai_service_with_files\", \"file_records_count\": 0, \"enhanced_with_cache\": true, \"file_total_violations\": 0}, \"query_timestamp\": \"2025-10-03T07:45:36.322789+00:00\", \"processing_time_seconds\": 2.1}',1,'',2.0962042808532715,'2025-10-03 07:45:36.322789',NULL),(14,'哪个摄像头违规最多？',24,0,'{\"eid\": \"371400228016303\", \"query\": \"哪个摄像头违规最多？\", \"success\": true, \"analysis\": {\"summary\": {\"total_records\": 0, \"active_cameras\": 0, \"time_description\": \"最近24小时\", \"total_violations\": 0}, \"recent_records\": [], \"violations_by_date\": {}, \"violations_by_hour\": {}, \"violations_by_type\": {}, \"violations_by_camera\": {}}, \"ai_summary\": \"暂无摄像头违规数据\", \"query_info\": {\"detected_keywords\": [\"camera\"], \"time_range_adjusted\": false}, \"data_source\": \"local_files_fallback\", \"fallback_reason\": \"AI服务响应超时（300秒），请稍后重试\", \"processing_mode\": \"local_only\", \"query_timestamp\": \"2025-10-03T07:50:38.403490+00:00\", \"time_range_hours\": 24, \"processing_time_seconds\": 302.05}',1,'',302.05099987983704,'2025-10-03 07:50:38.403490',NULL),(15,'今天违规情况如何？',24,0,'{\"eid\": \"VISITOR\", \"query\": \"今天违规情况如何？\", \"success\": true, \"analysis\": {}, \"ai_summary\": \"今日共记录 0 条检测记录，发现 0 次违规行为\", \"query_info\": {\"detected_keywords\": [\"today\"], \"time_range_adjusted\": false}, \"data_source\": \"local_files_fallback\", \"fallback_reason\": \"AI服务响应超时（300秒），请稍后重试\", \"processing_mode\": \"local_only\", \"query_timestamp\": \"2025-10-03T07:51:14.191402+00:00\", \"time_range_hours\": 24, \"processing_time_seconds\": 302.04}',1,'',302.041216135025,'2025-10-03 07:51:14.191402',NULL),(16,'口罩佩戴情况怎么样？',24,0,'{\"eid\": \"VISITOR\", \"query\": \"口罩佩戴情况怎么样？\", \"success\": true, \"analysis\": {}, \"ai_summary\": \"未检测到口罩相关违规\", \"query_info\": {\"detected_keywords\": [\"mask\"], \"time_range_adjusted\": false}, \"data_source\": \"local_files_fallback\", \"fallback_reason\": \"AI服务响应超时（300秒），请稍后重试\", \"processing_mode\": \"local_only\", \"query_timestamp\": \"2025-10-03T07:51:48.770979+00:00\", \"time_range_hours\": 24, \"processing_time_seconds\": 302.04}',1,'',302.0427613258362,'2025-10-03 07:51:48.770979',NULL),(17,'哪个摄像头违规最多？',24,0,'{\"eid\": \"371400228016303\", \"query\": \"哪个摄像头违规最多？\", \"success\": true, \"analysis\": {\"summary\": {\"total_records\": 0, \"active_cameras\": 0, \"time_description\": \"最近24小时\", \"total_violations\": 0}, \"recent_records\": [], \"violations_by_date\": {}, \"violations_by_hour\": {}, \"violations_by_type\": {}, \"violations_by_camera\": {}}, \"ai_summary\": \"暂无摄像头违规数据\", \"query_info\": {\"detected_keywords\": [\"camera\"], \"time_range_adjusted\": false}, \"data_source\": \"local_files_fallback\", \"fallback_reason\": \"AI服务响应超时（300秒），请稍后重试\", \"processing_mode\": \"local_only\", \"query_timestamp\": \"2025-10-03T07:52:25.380815+00:00\", \"time_range_hours\": 24, \"processing_time_seconds\": 302.05}',1,'',302.0451533794403,'2025-10-03 07:52:25.380815',NULL);
/*!40000 ALTER TABLE `ai_query_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=121 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add 系统配置',6,'add_systemconfig'),(22,'Can change 系统配置',6,'change_systemconfig'),(23,'Can delete 系统配置',6,'delete_systemconfig'),(24,'Can view 系统配置',6,'view_systemconfig'),(25,'Can add 违规记录',7,'add_violationrecord'),(26,'Can change 违规记录',7,'change_violationrecord'),(27,'Can delete 违规记录',7,'delete_violationrecord'),(28,'Can view 违规记录',7,'view_violationrecord'),(29,'Can add AI查询历史',8,'add_aiqueryhistory'),(30,'Can change AI查询历史',8,'change_aiqueryhistory'),(31,'Can delete AI查询历史',8,'delete_aiqueryhistory'),(32,'Can view AI查询历史',8,'view_aiqueryhistory'),(33,'Can add AI分析报告',9,'add_aianalysisreport'),(34,'Can change AI分析报告',9,'change_aianalysisreport'),(35,'Can delete AI分析报告',9,'delete_aianalysisreport'),(36,'Can view AI分析报告',9,'view_aianalysisreport'),(37,'Can add admin',10,'add_admin'),(38,'Can change admin',10,'change_admin'),(39,'Can delete admin',10,'delete_admin'),(40,'Can view admin',10,'view_admin'),(41,'Can add enterprise',11,'add_enterprise'),(42,'Can change enterprise',11,'change_enterprise'),(43,'Can delete enterprise',11,'delete_enterprise'),(44,'Can view enterprise',11,'view_enterprise'),(45,'Can add manager',12,'add_manager'),(46,'Can change manager',12,'change_manager'),(47,'Can delete manager',12,'delete_manager'),(48,'Can view manager',12,'view_manager'),(49,'Can add security problem',13,'add_securityproblem'),(50,'Can change security problem',13,'change_securityproblem'),(51,'Can delete security problem',13,'delete_securityproblem'),(52,'Can view security problem',13,'view_securityproblem'),(53,'Can add verification',14,'add_verification'),(54,'Can change verification',14,'change_verification'),(55,'Can delete verification',14,'delete_verification'),(56,'Can view verification',14,'view_verification'),(57,'Can add visitor',15,'add_visitor'),(58,'Can change visitor',15,'change_visitor'),(59,'Can delete visitor',15,'delete_visitor'),(60,'Can view visitor',15,'view_visitor'),(61,'Can add 人脸识别日志',16,'add_facerecognitionlog'),(62,'Can change 人脸识别日志',16,'change_facerecognitionlog'),(63,'Can delete 人脸识别日志',16,'delete_facerecognitionlog'),(64,'Can view 人脸识别日志',16,'view_facerecognitionlog'),(65,'Can add admin',17,'add_admin'),(66,'Can change admin',17,'change_admin'),(67,'Can delete admin',17,'delete_admin'),(68,'Can view admin',17,'view_admin'),(69,'Can add enterprise',18,'add_enterprise'),(70,'Can change enterprise',18,'change_enterprise'),(71,'Can delete enterprise',18,'delete_enterprise'),(72,'Can view enterprise',18,'view_enterprise'),(73,'Can add manager',19,'add_manager'),(74,'Can change manager',19,'change_manager'),(75,'Can delete manager',19,'delete_manager'),(76,'Can view manager',19,'view_manager'),(77,'Can add security problem',20,'add_securityproblem'),(78,'Can change security problem',20,'change_securityproblem'),(79,'Can delete security problem',20,'delete_securityproblem'),(80,'Can view security problem',20,'view_securityproblem'),(81,'Can add verification',21,'add_verification'),(82,'Can change verification',21,'change_verification'),(83,'Can delete verification',21,'delete_verification'),(84,'Can view verification',21,'view_verification'),(85,'Can add visitor',22,'add_visitor'),(86,'Can change visitor',22,'change_visitor'),(87,'Can delete visitor',22,'delete_visitor'),(88,'Can view visitor',22,'view_visitor'),(89,'Can add session',23,'add_session'),(90,'Can change session',23,'change_session'),(91,'Can delete session',23,'delete_session'),(92,'Can view session',23,'view_session'),(93,'Can add Video Source',24,'add_videosource'),(94,'Can change Video Source',24,'change_videosource'),(95,'Can delete Video Source',24,'delete_videosource'),(96,'Can view Video Source',24,'view_videosource'),(97,'Can add Violation Event',25,'add_violationevent'),(98,'Can change Violation Event',25,'change_violationevent'),(99,'Can delete Violation Event',25,'delete_violationevent'),(100,'Can view Violation Event',25,'view_violationevent'),(101,'Can add ROI Polygon',26,'add_roipolygon'),(102,'Can change ROI Polygon',26,'change_roipolygon'),(103,'Can delete ROI Polygon',26,'delete_roipolygon'),(104,'Can view ROI Polygon',26,'view_roipolygon'),(105,'Can add detection setting',27,'add_detectionsetting'),(106,'Can change detection setting',27,'change_detectionsetting'),(107,'Can delete detection setting',27,'delete_detectionsetting'),(108,'Can view detection setting',27,'view_detectionsetting'),(109,'Can add 设备仓库',28,'add_devicewarehouse'),(110,'Can change 设备仓库',28,'change_devicewarehouse'),(111,'Can delete 设备仓库',28,'delete_devicewarehouse'),(112,'Can view 设备仓库',28,'view_devicewarehouse'),(113,'Can add manager peer',29,'add_managerpeer'),(114,'Can change manager peer',29,'change_managerpeer'),(115,'Can delete manager peer',29,'delete_managerpeer'),(116,'Can view manager peer',29,'view_managerpeer'),(117,'Can add 仓库文件',30,'add_warehousefile'),(118,'Can change 仓库文件',30,'change_warehousefile'),(119,'Can delete 仓库文件',30,'delete_warehousefile'),(120,'Can view 仓库文件',30,'view_warehousefile');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$600000$Uv6SwQe20xX786aXCLCedB$wo3GA6jLmbzCYBw6Ihp7PWIq4+P/aCPdNSFqesv8E7o=','2025-10-05 12:10:02.321694',1,'yoga','','','2024379585@qq.com',1,1,'2025-10-05 12:08:31.094872');
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `detection_detectionsetting`
--

DROP TABLE IF EXISTS `detection_detectionsetting`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `detection_detectionsetting` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `confidence_threshold` double NOT NULL,
  `iou_threshold` double NOT NULL,
  `target_classes` varchar(255) NOT NULL,
  `enable_tracking` tinyint(1) NOT NULL,
  `save_snapshots` tinyint(1) NOT NULL,
  `video_source_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `video_source_id` (`video_source_id`),
  CONSTRAINT `detection_detections_video_source_id_9132c598_fk_detection` FOREIGN KEY (`video_source_id`) REFERENCES `detection_videosource` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detection_detectionsetting`
--

LOCK TABLES `detection_detectionsetting` WRITE;
/*!40000 ALTER TABLE `detection_detectionsetting` DISABLE KEYS */;
INSERT INTO `detection_detectionsetting` VALUES (1,0.5,0.45,'',1,1,1),(3,0.5,0.45,'',1,1,2),(4,0.5,0.45,'',1,1,3),(5,0.5,0.45,'',1,1,4),(6,0.5,0.45,'',1,1,5),(7,0.5,0.45,'',1,1,6),(8,0.5,0.45,'',1,1,7),(9,0.5,0.45,'',1,1,8),(10,0.5,0.45,'',1,1,9),(11,0.5,0.45,'',1,1,10),(12,0.5,0.45,'',1,1,11),(13,0.5,0.45,'',1,1,12),(14,0.5,0.45,'',1,1,13),(15,0.5,0.45,'',1,1,14),(16,0.5,0.45,'',1,1,15),(17,0.5,0.45,'',1,1,16),(18,0.5,0.45,'',1,1,17),(19,0.5,0.45,'',1,1,18),(20,0.5,0.45,'',1,1,19),(21,0.5,0.45,'',1,1,20),(22,0.5,0.45,'',1,1,21),(23,0.5,0.45,'',1,1,22),(24,0.5,0.45,'',1,1,23),(25,0.5,0.45,'',1,1,24),(26,0.5,0.45,'',1,1,25),(27,0.5,0.45,'',1,1,26),(28,0.5,0.45,'',1,1,27),(29,0.5,0.45,'',1,1,28);
/*!40000 ALTER TABLE `detection_detectionsetting` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `detection_roipolygon`
--

DROP TABLE IF EXISTS `detection_roipolygon`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `detection_roipolygon` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `points` longtext NOT NULL,
  `active` tinyint(1) NOT NULL,
  `video_source_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `detection_roipolygon_video_source_id_dac1ec1d_fk_detection` (`video_source_id`),
  CONSTRAINT `detection_roipolygon_video_source_id_dac1ec1d_fk_detection` FOREIGN KEY (`video_source_id`) REFERENCES `detection_videosource` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detection_roipolygon`
--

LOCK TABLES `detection_roipolygon` WRITE;
/*!40000 ALTER TABLE `detection_roipolygon` DISABLE KEYS */;
INSERT INTO `detection_roipolygon` VALUES (1,'ROI-1760103252202','[[0.47125142544904397,0.10678051569798451],[0.4589070772979954,0.3834525016807879],[0.5263262095075684,0.9567968581752722],[0.7200375189547921,0.9701304478611904]]',1,1),(2,'ROI-1760166842618','[[0.4161766413905196,0.01361903625466432],[0.34875750918094667,0.9636373013763387],[0.6298288209278986,0.976970891062257],[0.48169664311531585,0.01028563883318476]]',1,2),(3,'ROI-1760253316209','[[0.36679924878632536,0.04279012932682727],[0.3639505530591603,0.13612525712825493],[0.684903604986423,0.8594724975893193],[0.7238357799243454,0.4894653838050882]]',1,8),(4,'ROI-1760339669006','[[0.21706829754321716,0.2710725209302463],[0.18952039418303943,0.3557546790264852],[0.7555853761324979,0.7431251539616448],[0.9430888473904818,0.5011761308295336]]',1,15),(5,'ROI-1762506991138','[[0.2246711254252291,0.2736768320501235],[0.2051210004599417,0.3318958157412878],[0.845831914095043,0.6857462620720005],[0.9409166127898501,0.504284494722917]]',1,27);
/*!40000 ALTER TABLE `detection_roipolygon` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `detection_videosource`
--

DROP TABLE IF EXISTS `detection_videosource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `detection_videosource` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `source_type` varchar(10) NOT NULL,
  `source_url` varchar(255) NOT NULL,
  `active` tinyint(1) NOT NULL,
  `resolution_width` int NOT NULL,
  `resolution_height` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detection_videosource`
--


--
-- Table structure for table `device_warehouses`
--

DROP TABLE IF EXISTS `device_warehouses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `device_warehouses` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '仓库名称',
  `eid` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '企业EID',
  `warehouse_type` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'json' COMMENT '仓库类型',
  `created_at` datetime(6) NOT NULL COMMENT '创建时间',
  `updated_at` datetime(6) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备仓库';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device_warehouses`
--

LOCK TABLES `device_warehouses` WRITE;
/*!40000 ALTER TABLE `device_warehouses` DISABLE KEYS */;
INSERT INTO `device_warehouses` VALUES (1,'device_1','914403007MA1234567X','json','2025-09-27 08:37:45.593466','2025-09-27 08:37:45.593466'),(2,'device_1','371400228016303','json','2025-10-01 07:40:05.604309','2025-10-01 07:40:05.604309'),(3,'device_2','371400228016303','mp4','2025-10-11 07:05:00.901365','2025-10-11 07:05:00.901365');
/*!40000 ALTER TABLE `device_warehouses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
INSERT INTO `django_admin_log` VALUES (1,'2025-10-05 12:14:00.731677','1','test1 (file)',1,'[{\"added\": {}}]',24,1);
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(17,'api','admin'),(18,'api','enterprise'),(19,'api','manager'),(20,'api','securityproblem'),(21,'api','verification'),(22,'api','visitor'),(3,'auth','group'),(2,'auth','permission'),(4,'auth','user'),(10,'authentication','admin'),(11,'authentication','enterprise'),(12,'authentication','manager'),(13,'authentication','securityproblem'),(14,'authentication','verification'),(15,'authentication','visitor'),(5,'contenttypes','contenttype'),(27,'detection','detectionsetting'),(26,'detection','roipolygon'),(24,'detection','videosource'),(25,'detection','violationevent'),(16,'face_recognition','facerecognitionlog'),(9,'monitor','aianalysisreport'),(8,'monitor','aiqueryhistory'),(28,'monitor','devicewarehouse'),(29,'monitor','managerpeer'),(6,'monitor','systemconfig'),(7,'monitor','violationrecord'),(30,'monitor','warehousefile'),(23,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2025-08-30 06:47:47.982536'),(2,'auth','0001_initial','2025-08-30 06:47:48.454293'),(3,'admin','0001_initial','2025-08-30 06:47:48.565108'),(4,'admin','0002_logentry_remove_auto_add','2025-08-30 06:47:48.565108'),(5,'admin','0003_logentry_add_action_flag_choices','2025-08-30 06:47:48.586900'),(6,'api','0001_initial','2025-08-30 06:50:38.507705'),(7,'contenttypes','0002_remove_content_type_name','2025-08-30 06:50:57.239969'),(8,'auth','0002_alter_permission_name_max_length','2025-08-30 06:50:57.279954'),(9,'auth','0003_alter_user_email_max_length','2025-08-30 06:50:57.295765'),(10,'auth','0004_alter_user_username_opts','2025-08-30 06:50:57.295765'),(11,'auth','0005_alter_user_last_login_null','2025-08-30 06:50:57.358632'),(12,'auth','0006_require_contenttypes_0002','2025-08-30 06:50:57.358632'),(13,'auth','0007_alter_validators_add_error_messages','2025-08-30 06:50:57.358632'),(14,'auth','0008_alter_user_username_max_length','2025-08-30 06:50:57.422668'),(15,'auth','0009_alter_user_last_name_max_length','2025-08-30 06:50:57.469300'),(16,'auth','0010_alter_group_name_max_length','2025-08-30 06:50:57.485298'),(17,'auth','0011_update_proxy_permissions','2025-08-30 06:50:57.485298'),(18,'auth','0012_alter_user_first_name_max_length','2025-08-30 06:50:57.539923'),(19,'authentication','0001_initial','2025-08-30 06:50:57.549052'),(20,'face_recognition','0001_initial','2025-08-30 06:50:57.564691'),(21,'monitor','0001_initial','2025-08-30 06:50:57.770642'),(22,'monitor','0002_add_image_path_field','2025-08-30 06:53:56.098612'),(23,'monitor','0003_alter_violationrecord_image_path','2025-08-30 06:54:04.980795'),(24,'monitor','0004_remove_aianalysisreport_violation_record_and_more','2025-08-30 06:54:13.882545'),(25,'sessions','0001_initial','2025-08-30 06:54:22.803246'),(26,'detection','0001_initial','2025-10-05 10:12:26.408441'),(27,'detection','0002_alter_violationevent_table','2025-10-05 10:12:26.418891'),(28,'monitor','0004_devicewarehouse_managerpeer_warehousefile','2025-10-05 10:14:02.285823');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `enterprise`
--

DROP TABLE IF EXISTS `enterprise`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `enterprise` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Name` varchar(100) DEFAULT NULL,
  `EID` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `enterprise`
--

LOCK TABLES `enterprise` WRITE;
/*!40000 ALTER TABLE `enterprise` DISABLE KEYS */;
INSERT INTO `enterprise` VALUES (1,'科技创新有限公司','914403007MA1234567X'),(2,'智能制造集团','914403007MA9876543K'),(5,'山东祥瑞广告装饰有限公司','371400228016303');
/*!40000 ALTER TABLE `enterprise` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `face_recognition_log`
--

DROP TABLE IF EXISTS `face_recognition_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `face_recognition_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_name` varchar(100) DEFAULT NULL,
  `is_real_person` tinyint(1) NOT NULL,
  `status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `face_recognition_log`
--

LOCK TABLES `face_recognition_log` WRITE;
/*!40000 ALTER TABLE `face_recognition_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `face_recognition_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `manager`
--

DROP TABLE IF EXISTS `manager`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `manager` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Name` varchar(100) DEFAULT NULL,
  `EID` varchar(50) DEFAULT NULL,
  `Password` varchar(100) DEFAULT NULL,
  `Rep` varchar(10) DEFAULT 'No',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `manager`
--

LOCK TABLES `manager` WRITE;
/*!40000 ALTER TABLE `manager` DISABLE KEYS */;
INSERT INTO `manager` VALUES (1,'陈志强','914403007MA1234567X','Chen@Mgr789','Yes'),(2,'刘美华','914403007MA9876543K','Liu#Boss2024','Yes'),(3,'赵文博','914403007MA1234567X','Zhao$Lead321','No'),(4,'manager','914403007MA1234567X','qpwoeiruty123!','No'),(8,'张海宽','371400228016303','qpwoeiruty123!','yes'),(9,'朱志德','371400228016303','qpwoeiruty123!','no');
/*!40000 ALTER TABLE `manager` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `manager_peers`
--

DROP TABLE IF EXISTS `manager_peers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `manager_peers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `manager_name` varchar(100) NOT NULL,
  `eid` varchar(50) NOT NULL,
  `peer_id` varchar(255) DEFAULT NULL,
  `signal_endpoint` varchar(255) DEFAULT NULL,
  `last_heartbeat` timestamp NULL DEFAULT NULL,
  `is_online` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_manager_eid` (`manager_name`,`eid`),
  KEY `idx_eid_online` (`eid`,`is_online`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `manager_peers`
--

LOCK TABLES `manager_peers` WRITE;
/*!40000 ALTER TABLE `manager_peers` DISABLE KEYS */;
/*!40000 ALTER TABLE `manager_peers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `security_problem`
--

DROP TABLE IF EXISTS `security_problem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `security_problem` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Name` varchar(100) DEFAULT NULL,
  `Problem1` text,
  `Answer1` text,
  `Problem2` text,
  `Answer2` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `security_problem`
--

LOCK TABLES `security_problem` WRITE;
/*!40000 ALTER TABLE `security_problem` DISABLE KEYS */;
INSERT INTO `security_problem` VALUES (1,'张伟明','您的出生城市是？','北京','您最喜欢的颜色是？','蓝色'),(2,'王小丽','您的出生城市是？','上海','您最喜欢的颜色是？','红色'),(3,'李建国','您的出生城市是？','广州','您最喜欢的颜色是？','绿色'),(4,'陈志强','您的出生城市是？','深圳','您最喜欢的颜色是？','黄色'),(5,'刘美华','您的出生城市是？','杭州','您最喜欢的颜色是？','紫色'),(6,'赵文博','您的出生城市是？','成都','您最喜欢的颜色是？','橙色'),(7,'孙晓军','您的出生城市是？','南京','您最喜欢的颜色是？','白色'),(8,'周雨萱','您的出生城市是？','天津','您最喜欢的颜色是？','黑色'),(9,'吴俊杰','您的出生城市是？','重庆','您最喜欢的颜色是？','灰色'),(10,'employee','您的出生城市是？','广州','您最喜欢的颜色是？','卡其色');
/*!40000 ALTER TABLE `security_problem` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `share_tokens`
--

DROP TABLE IF EXISTS `share_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `share_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token` varchar(64) NOT NULL,
  `repository_id` int NOT NULL,
  `created_by` int NOT NULL,
  `valid_days` int NOT NULL,
  `expires_at` datetime NOT NULL,
  `access_count` int DEFAULT '0',
  `max_access_count` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('active','expired','revoked') DEFAULT 'active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `repository_id` (`repository_id`),
  KEY `created_by` (`created_by`),
  KEY `idx_token` (`token`),
  KEY `idx_expires_at` (`expires_at`),
  CONSTRAINT `share_tokens_ibfk_1` FOREIGN KEY (`repository_id`) REFERENCES `video_repositories` (`id`) ON DELETE CASCADE,
  CONSTRAINT `share_tokens_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `share_tokens`
--

LOCK TABLES `share_tokens` WRITE;
/*!40000 ALTER TABLE `share_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `share_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_config`
--

DROP TABLE IF EXISTS `system_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `key` varchar(100) NOT NULL,
  `value` longtext NOT NULL,
  `description` longtext NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_config`
--

LOCK TABLES `system_config` WRITE;
/*!40000 ALTER TABLE `system_config` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `storage_path` varchar(500) DEFAULT './user_videos',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `verification`
--

DROP TABLE IF EXISTS `verification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `verification` (
  `Name` varchar(50) NOT NULL,
  `Email` varchar(100) NOT NULL,
  PRIMARY KEY (`Name`),
  UNIQUE KEY `Email` (`Email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `verification`
--

LOCK TABLES `verification` WRITE;
/*!40000 ALTER TABLE `verification` DISABLE KEYS */;
INSERT INTO `verification` VALUES ('employee','20233802051@m.scnu.edu.cn'),('manager','2024379585@qq.com'),('李迪聪','2232840862@qq.com'),('朱志德','2837140090@qq.com'),('陈志强','chen.manager@outlook.com'),('张海宽','kipolit@qq.com'),('李建国','li.visitor@163.com'),('刘美华','liu.manager@techcorp.com'),('孙晓军','sun_admin@126.com'),('王小丽','wang_visitor@qq.com'),('吴俊杰','wu.admin@gmail.com'),('张伟明','zhang.visitor@gmail.com'),('赵文博','zhao.manager@yahoo.com'),('周雨萱','zhou.admin@sina.com');
/*!40000 ALTER TABLE `verification` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `video_repositories`
--

DROP TABLE IF EXISTS `video_repositories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `video_repositories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `repository_name` varchar(100) NOT NULL,
  `is_public` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_repo` (`user_id`,`repository_name`),
  CONSTRAINT `video_repositories_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `video_repositories`
--

LOCK TABLES `video_repositories` WRITE;
/*!40000 ALTER TABLE `video_repositories` DISABLE KEYS */;
/*!40000 ALTER TABLE `video_repositories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `videos`
--

DROP TABLE IF EXISTS `videos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `videos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `repository_id` int NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `original_name` varchar(255) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `file_size` bigint NOT NULL,
  `duration` int DEFAULT NULL,
  `upload_date` date NOT NULL,
  `upload_time` time NOT NULL,
  `metadata` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `repository_id` (`repository_id`),
  KEY `idx_upload_date` (`upload_date`),
  CONSTRAINT `videos_ibfk_1` FOREIGN KEY (`repository_id`) REFERENCES `video_repositories` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `videos`
--

LOCK TABLES `videos` WRITE;
/*!40000 ALTER TABLE `videos` DISABLE KEYS */;
/*!40000 ALTER TABLE `videos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `violation_events`
--

DROP TABLE IF EXISTS `violation_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `violation_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `timestamp` datetime(6) NOT NULL,
  `snapshot` varchar(100) NOT NULL,
  `zoomed_snapshot` varchar(100) DEFAULT NULL,
  `detection_data` longtext NOT NULL,
  `confidence` double NOT NULL,
  `status` varchar(20) NOT NULL,
  `notes` longtext NOT NULL,
  `video_source_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `detection_violatione_video_source_id_2b97e47a_fk_detection` (`video_source_id`),
  CONSTRAINT `detection_violatione_video_source_id_2b97e47a_fk_detection` FOREIGN KEY (`video_source_id`) REFERENCES `detection_videosource` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `violation_events`
--

LOCK TABLES `violation_events` WRITE;
/*!40000 ALTER TABLE `violation_events` DISABLE KEYS */;
/*!40000 ALTER TABLE `violation_events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `violations_records`
--

DROP TABLE IF EXISTS `violations_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `violations_records` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `camera_id` varchar(50) NOT NULL,
  `detection_timestamp` datetime(6) NOT NULL,
  `violation_data` json NOT NULL,
  `image_path` varchar(500) DEFAULT NULL,
  `total_violations` int NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `violations__camera__9a903f_idx` (`camera_id`,`detection_timestamp`),
  KEY `violations__created_e7a4be_idx` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `violations_records`
--

LOCK TABLES `violations_records` WRITE;
/*!40000 ALTER TABLE `violations_records` DISABLE KEYS */;
/*!40000 ALTER TABLE `violations_records` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `visitor`
--

DROP TABLE IF EXISTS `visitor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `visitor` (
  `id` int NOT NULL AUTO_INCREMENT,
  `Name` varchar(100) DEFAULT NULL,
  `Password` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `visitor`
--

LOCK TABLES `visitor` WRITE;
/*!40000 ALTER TABLE `visitor` DISABLE KEYS */;
INSERT INTO `visitor` VALUES (1,'张伟明','qpwoeiruty123!'),(2,'王小丽','Wang#Visit123'),(3,'李建国','Li$Secure456'),(5,'李迪聪','qpwoeiruty123!'),(7,'employee','qpwoeiruty123!');
/*!40000 ALTER TABLE `visitor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `warehouse_files`
--

DROP TABLE IF EXISTS `warehouse_files`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `warehouse_files` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `warehouse_id` int NOT NULL COMMENT '关联仓库ID',
  `file_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件名',
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `upload_date` date NOT NULL COMMENT '上传日期',
  `eid` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '关联EID',
  `file_size` bigint NOT NULL COMMENT '文件大小',
  `file_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'json' COMMENT '文件类型',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'uploaded' COMMENT '状态',
  `created_at` datetime(6) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `warehouse_files_warehouse_id_fk` (`warehouse_id`),
  KEY `warehouse_files_eid_upload_date_idx` (`eid`,`upload_date`),
  CONSTRAINT `warehouse_files_warehouse_id_fk` FOREIGN KEY (`warehouse_id`) REFERENCES `device_warehouses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仓库文件';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `warehouse_files`
--

LOCK TABLES `warehouse_files` WRITE;
/*!40000 ALTER TABLE `warehouse_files` DISABLE KEYS */;
INSERT INTO `warehouse_files` VALUES (1,1,'D11_20240907170658_4_second_frame_100.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_4_second_frame_100.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.698898'),(2,1,'D11_20240907170658_5_second_frame_125.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_5_second_frame_125.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.749862'),(3,1,'D11_20240907170658_6_second_frame_150.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_6_second_frame_150.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.750918'),(4,1,'D11_20240907170658_7_second_frame_175.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_7_second_frame_175.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.760838'),(5,1,'D11_20240907170658_8_second_frame_200.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_8_second_frame_200.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.765908'),(6,1,'D11_20240907170658_9_second_frame_225.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_9_second_frame_225.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.765908'),(7,1,'D11_20240907170658_10_second_frame_250.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_10_second_frame_250.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.771270'),(8,1,'D11_20240907170658_0_second_frame_0.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_0_second_frame_0.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.776696'),(9,1,'D11_20240907170658_1_second_frame_25.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_1_second_frame_25.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.776696'),(10,1,'D11_20240907170658_2_second_frame_50.json','enterprise_archives/914403007MA1234567X/1/2025-09-27/D11_20240907170658_2_second_frame_50.json','2025-09-27','914403007MA1234567X',406,'json','uploaded','2025-09-27 08:37:54.782132'),(12,1,'D34_20240907171919_8077_second_frame_121155.json','warehouses\\1\\2025-09-28\\b29ae7e04d8c43569cc8b7b825c20c6a.json','2025-09-28','914403007MA1234567X',406,'json','uploaded','2025-09-28 07:21:55.614574'),(13,2,'D11_20240907170658_4_second_frame_100.json','warehouses\\2\\2025-10-01\\3fff7396da004b97a36164777efce66e.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.005695'),(14,2,'D11_20240907170658_5_second_frame_125.json','warehouses\\2\\2025-10-01\\c59c055ab9464bf3a53e244c74280fa2.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.015698'),(15,2,'D11_20240907170658_6_second_frame_150.json','warehouses\\2\\2025-10-01\\a32ec45abd86498889d768a095b8c37a.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.018698'),(16,2,'D11_20240907170658_7_second_frame_175.json','warehouses\\2\\2025-10-01\\850450b286af429bbeda8f4b174c27b5.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.023748'),(17,2,'D11_20240907170658_8_second_frame_200.json','warehouses\\2\\2025-10-01\\96d40791327946c8b2292b06366f9a1e.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.026745'),(18,2,'D11_20240907170658_9_second_frame_225.json','warehouses\\2\\2025-10-01\\9ebcbed994b64c78959a2c9aec4f7015.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.030231'),(19,2,'D11_20240907170658_10_second_frame_250.json','warehouses\\2\\2025-10-01\\7561699b48514e37b9b04d160370dad4.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.034413'),(20,2,'D11_20240907170658_11_second_frame_275.json','warehouses\\2\\2025-10-01\\deb3d60fa3eb441f87623db008430252.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.036988'),(21,2,'D11_20240907170658_0_second_frame_0.json','warehouses\\2\\2025-10-01\\e8c1069b296b42b0b2b1c88e885dc3fc.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.040143'),(22,2,'D11_20240907170658_1_second_frame_25.json','warehouses\\2\\2025-10-01\\c2aea655926a46ca8d3661ca98ff587d.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.044235'),(23,2,'D11_20240907170658_2_second_frame_50.json','warehouses\\2\\2025-10-01\\c0f122c667bb435583e9be726ecb5887.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.048276'),(24,2,'D11_20240907170658_3_second_frame_75.json','warehouses\\2\\2025-10-01\\df8efaa04b8f49d49c63d5798d2d942a.json','2025-10-01','371400228016303',406,'json','uploaded','2025-10-01 07:40:36.051908'),(25,3,'74dd5b9403cf4723b4ed81d1abbbce5a.mp4','warehouses\\3\\2025-10-11\\74dd5b9403cf4723b4ed81d1abbbce5a.mp4','2025-10-11','371400228016303',35704148,'mp4','uploaded','2025-10-11 07:05:20.312812'),(26,3,'1eabf158a11346e29025e44c78d7314a.mp4','warehouses\\3\\2025-10-11\\1eabf158a11346e29025e44c78d7314a.mp4','2025-10-11','371400228016303',23475449,'mp4','uploaded','2025-10-11 07:05:20.396074'),(27,3,'ec47431440af4dd085df083d08702cd1.mp4','warehouses\\3\\2025-10-11\\ec47431440af4dd085df083d08702cd1.mp4','2025-10-11','371400228016303',23475449,'mp4','uploaded','2025-10-11 07:05:20.396074');
/*!40000 ALTER TABLE `warehouse_files` ENABLE KEYS */;
UNLOCK TABLES;

/*!40101 SET character_set_client = @saved_cs_client */;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-07 18:27:48
