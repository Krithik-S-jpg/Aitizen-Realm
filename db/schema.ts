// Intentionally empty by default.
// Add Drizzle tables here when the site actually needs a database.
// See examples/d1/db/schema.ts for an opt-in example.
import { sqliteTable, text, integer, index } from "drizzle-orm/sqlite-core";
export const records = sqliteTable("observer_records", {
  id: text("id").primaryKey(), kind: text("kind").notNull(),
  created: integer("created").notNull(), payload: text("payload").notNull(),
}, table => [index("observer_kind_time").on(table.kind, table.created)]);
