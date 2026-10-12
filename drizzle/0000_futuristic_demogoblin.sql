CREATE TABLE `observer_records` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text NOT NULL,
	`created` integer NOT NULL,
	`payload` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `observer_kind_time` ON `observer_records` (`kind`,`created`);