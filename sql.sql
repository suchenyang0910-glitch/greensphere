
CREATE TABLE `telegram_users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `telegram_id` bigint(20) NOT NULL,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `first_name` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_name` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `telegram_id` (`telegram_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

CREATE TABLE `quests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `points` int(11) DEFAULT '0',
  `active` tinyint(1) DEFAULT '1',
  `expires_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

CREATE TABLE `quest_submissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `telegram_id` bigint(20) NOT NULL,
  `quest_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `submitted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `submit_date` date GENERATED ALWAYS AS (cast(`submitted_at` as date)) STORED,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_user_quest_day` (`telegram_id`,`quest_code`,`submit_date`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

CREATE TABLE `point_transactions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `telegram_id` bigint(20) NOT NULL,
  `points` int(11) NOT NULL,
  `source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

CREATE TABLE `leafpass_nft` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `telegram_id` bigint(20) NOT NULL,
  `level` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `token_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chain` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `minted` tinyint(1) DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

CREATE TABLE `leafpass_status` (
  `telegram_id` bigint(20) NOT NULL,
  `level` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_points` int(11) DEFAULT '0',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`telegram_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci