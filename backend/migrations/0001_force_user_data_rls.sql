-- MarketLens security migration 0001
--
-- The migration runner safely substitutes {runtime_role} as a PostgreSQL
-- identifier. Do not execute this template through ad-hoc string replacement.

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO {runtime_role};
REVOKE CREATE ON SCHEMA public FROM {runtime_role};

REVOKE ALL ON TABLE saved_jobs FROM PUBLIC;
REVOKE ALL ON TABLE saved_reports FROM PUBLIC;
REVOKE ALL ON TABLE career_plan_runs FROM PUBLIC;
REVOKE ALL ON TABLE career_plan_steps FROM PUBLIC;
REVOKE ALL ON TABLE career_plan_audit_events FROM PUBLIC;
REVOKE ALL ON TABLE job_postings FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE job_postings TO {runtime_role};
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE saved_jobs TO {runtime_role};
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE saved_reports TO {runtime_role};
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE career_plan_runs TO {runtime_role};
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE career_plan_steps TO {runtime_role};
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE career_plan_audit_events TO {runtime_role};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {runtime_role};

ALTER TABLE saved_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_jobs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS marketlens_saved_jobs_owner ON saved_jobs;
CREATE POLICY marketlens_saved_jobs_owner
ON saved_jobs
FOR ALL
TO {runtime_role}
USING (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')
)
WITH CHECK (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')
);

ALTER TABLE saved_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS marketlens_saved_reports_owner ON saved_reports;
CREATE POLICY marketlens_saved_reports_owner
ON saved_reports
FOR ALL
TO {runtime_role}
USING (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')
)
WITH CHECK (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')
);

ALTER TABLE career_plan_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_plan_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS marketlens_career_plan_runs_owner ON career_plan_runs;
CREATE POLICY marketlens_career_plan_runs_owner
ON career_plan_runs
FOR ALL
TO {runtime_role}
USING (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')
)
WITH CHECK (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')
);

ALTER TABLE career_plan_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_plan_steps FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS marketlens_career_plan_steps_owner ON career_plan_steps;
CREATE POLICY marketlens_career_plan_steps_owner
ON career_plan_steps
FOR ALL
TO {runtime_role}
USING (
    EXISTS (
        SELECT 1
        FROM career_plan_runs
        WHERE career_plan_runs.id = career_plan_steps.run_id
          AND career_plan_runs.user_id = NULLIF(current_setting('app.current_user_id', true), '')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM career_plan_runs
        WHERE career_plan_runs.id = career_plan_steps.run_id
          AND career_plan_runs.user_id = NULLIF(current_setting('app.current_user_id', true), '')
    )
);

ALTER TABLE career_plan_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_plan_audit_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS marketlens_career_plan_audit_events_owner ON career_plan_audit_events;
CREATE POLICY marketlens_career_plan_audit_events_owner
ON career_plan_audit_events
FOR ALL
TO {runtime_role}
USING (
    EXISTS (
        SELECT 1
        FROM career_plan_runs
        WHERE career_plan_runs.id = career_plan_audit_events.run_id
          AND career_plan_runs.user_id = NULLIF(current_setting('app.current_user_id', true), '')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM career_plan_runs
        WHERE career_plan_runs.id = career_plan_audit_events.run_id
          AND career_plan_runs.user_id = NULLIF(current_setting('app.current_user_id', true), '')
    )
);

REVOKE ALL ON TABLE marketlens_schema_migrations FROM PUBLIC;
REVOKE ALL ON TABLE marketlens_schema_migrations FROM {runtime_role};
