CREATE UNIQUE INDEX idx_revisions_entity_version
    ON revisions(entity_type, entity_id, version);

CREATE UNIQUE INDEX idx_campaign_items_plan_order
    ON campaign_items(plan_id, "order");
