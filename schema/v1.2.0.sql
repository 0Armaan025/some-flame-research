-- ============================================================================
-- Combustion Research Database Schema  v1.2.0-candidate  (DESIGN ONLY)
-- FLEX / JAXA group combustion / TNF
--
-- STATUS: candidate. This file is a written specification consolidated from
-- the design review thread. It has NOT been loaded into any SQLite database,
-- and no test in validation-matrix.md has been executed. Do not label this
-- schema validated until a real SQLite build-and-test harness has run.
--
-- Insertion contract (supported order; no deferred foreign keys):
--   experimental_run -> anchor event -> time_reference -> interpreted event
-- An anchor event normally has time_reference_id = NULL. An interpreted event
-- (or measurement) points at a time_reference via event.time_reference_id /
-- measurement.time_reference_id; that time_reference is anchored on the anchor
-- event via time_reference.reference_event_id. The four self-anchor triggers
-- below prevent an event from being its own time anchor. Because the self-
-- anchor case is rejected structurally, no circular insert is ever required,
-- so PRAGMA defer_foreign_keys is NOT part of the supported contract.
-- ============================================================================

PRAGMA foreign_keys = ON;   -- per-connection; must be set outside any transaction

-- ----------------------------------------------------------------------------
-- 1. source
-- ----------------------------------------------------------------------------
CREATE TABLE source (
    source_id           TEXT PRIMARY KEY,
    doi                 TEXT UNIQUE,
    publication_title   TEXT NOT NULL,
    authors             TEXT NOT NULL CHECK (
        CASE WHEN json_valid(authors) THEN json_type(authors) = 'array' ELSE 0 END),
    year                INTEGER CHECK (year IS NULL OR (year >= 1900 AND year <= 2100)),
    url                 TEXT,
    publisher           VARCHAR(255),
    document_type       VARCHAR(50) NOT NULL CHECK (document_type IN (
        'peer-reviewed_journal','nasa_psi','technical_report','thesis',
        'conference_proceedings','preprint','other')),
    data_origin         VARCHAR(100) NOT NULL,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Element type validation cannot be expressed in a CHECK (no subqueries).
-- json_each exposes each element's JSON type in its "type" column.
CREATE TRIGGER trg_source_authors_ins
BEFORE INSERT ON source
FOR EACH ROW WHEN NEW.authors IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'source.authors must be a JSON array of strings')
    WHERE EXISTS (SELECT 1 FROM json_each(NEW.authors) WHERE json_each.type <> 'text');
END;

CREATE TRIGGER trg_source_authors_upd
BEFORE UPDATE OF authors ON source
FOR EACH ROW WHEN NEW.authors IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'source.authors must be a JSON array of strings')
    WHERE EXISTS (SELECT 1 FROM json_each(NEW.authors) WHERE json_each.type <> 'text');
END;

-- ----------------------------------------------------------------------------
-- 2. experiment
-- ----------------------------------------------------------------------------
CREATE TABLE experiment (
    experiment_id         TEXT PRIMARY KEY,
    experiment_label      VARCHAR(100) NOT NULL UNIQUE,
    experiment_title      TEXT,
    principal_investigator TEXT,
    managing_center       VARCHAR(100),
    start_date            TEXT,
    end_date              TEXT,
    research_area         VARCHAR(100),
    sub_research_area     VARCHAR(100),
    funding_grant         VARCHAR(100),
    flight_platform       VARCHAR(100),
    experiment_hardware   TEXT,
    objective             TEXT,
    hypothesis            TEXT,
    notes                 TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- 3. chemical_species  (chemical_formula is NOT unique)
-- ----------------------------------------------------------------------------
CREATE TABLE chemical_species (
    species_id        TEXT PRIMARY KEY,
    species_name      VARCHAR(100) NOT NULL,
    chemical_formula  VARCHAR(50),
    notes             TEXT
);

-- ----------------------------------------------------------------------------
-- 4. clock_domain (optional association for a time reference; not every
--    reference has an instrument clock domain)
-- ----------------------------------------------------------------------------
CREATE TABLE clock_domain (
    clock_domain_id       TEXT PRIMARY KEY,
    domain_name           VARCHAR(100) NOT NULL UNIQUE,
    domain_description    TEXT,
    instrument_association VARCHAR(100),
    time_unit             VARCHAR(20) NOT NULL DEFAULT 's'
                          CHECK (time_unit IN ('s','ms','us','ns','frame','count','other')),
    notes                 TEXT
);

-- ----------------------------------------------------------------------------
-- 5. data_file (SHA-256 is an integrity identifier, not identity;
--    relative_path is the logical identity)
-- ----------------------------------------------------------------------------
CREATE TABLE data_file (
    file_id                 TEXT PRIMARY KEY,
    relative_path           TEXT NOT NULL UNIQUE,
    file_name               VARCHAR(255) NOT NULL,
    file_format             VARCHAR(30) NOT NULL,
    file_size_bytes         BIGINT NOT NULL CHECK (file_size_bytes >= 0),
    sha256_checksum         VARCHAR(64) NOT NULL CHECK (
        length(sha256_checksum) = 64
        AND lower(sha256_checksum) = sha256_checksum
        AND sha256_checksum NOT GLOB '*[^0-9a-f]*'),
    crc32_checksum          VARCHAR(10),
    is_archive              INTEGER NOT NULL DEFAULT 0 CHECK (is_archive IN (0,1)),
    archive_member_count    INTEGER CHECK (archive_member_count IS NULL OR archive_member_count >= 0),
    image_format            VARCHAR(10),
    image_count             INTEGER CHECK (image_count IS NULL OR image_count >= 0),
    missing_ranges          TEXT,
    availability_notes      TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now')),
    -- An archive's member count may be unknown (not yet inspected); a
    -- non-archive must not carry a member count.
    CHECK (is_archive = 1 OR archive_member_count IS NULL)
);

-- ----------------------------------------------------------------------------
-- 6. source_experiment (many-to-many)
-- ----------------------------------------------------------------------------
CREATE TABLE source_experiment (
    source_experiment_id TEXT PRIMARY KEY,
    source_id            TEXT NOT NULL REFERENCES source(source_id),
    experiment_id        TEXT NOT NULL REFERENCES experiment(experiment_id),
    description_in_source TEXT,
    extraction_confidence VARCHAR(20) NOT NULL CHECK (extraction_confidence IN ('high','medium','low')),
    extraction_method    VARCHAR(100) NOT NULL,
    notes                TEXT,
    UNIQUE (source_id, experiment_id)
);

-- ----------------------------------------------------------------------------
-- 7. extraction_record (where in the source a value was found and how it was
--    extracted; data_file_id links a managed source file when applicable)
-- ----------------------------------------------------------------------------
CREATE TABLE extraction_record (
    extraction_record_id TEXT PRIMARY KEY,
    source_id            TEXT NOT NULL REFERENCES source(source_id),
    data_file_id         TEXT REFERENCES data_file(file_id),
    page                 VARCHAR(50),
    table_figure         VARCHAR(100),
    file_path            TEXT,
    column_name          VARCHAR(100),
    row_identifier       TEXT,
    extraction_method    VARCHAR(100) NOT NULL CHECK (extraction_method IN (
        'direct_export','manual_transcription','graph_digitization','ocr','api_query')),
    extraction_confidence VARCHAR(20) NOT NULL CHECK (extraction_confidence IN ('high','medium','low')),
    digitization_tool    VARCHAR(100),
    extraction_date      TEXT NOT NULL DEFAULT (datetime('now')),
    extracted_by         VARCHAR(100),
    verification_status  VARCHAR(30) NOT NULL DEFAULT 'unverified'
                         CHECK (verification_status IN ('unverified','verified','disputed')),
    verification_notes   TEXT
);

-- ----------------------------------------------------------------------------
-- 8. experimental_run (authoritative composition lives ONLY in run_composition)
-- ----------------------------------------------------------------------------
CREATE TABLE experimental_run (
    run_id                          TEXT PRIMARY KEY,
    experiment_id                   TEXT NOT NULL REFERENCES experiment(experiment_id),
    run_label                       VARCHAR(100) NOT NULL,
    run_number                      INTEGER CHECK (run_number IS NULL OR run_number > 0),
    test_date                       TEXT,
    test_time                       TEXT,
    run_datetime_original           TEXT,
    run_time_standard               VARCHAR(30) NOT NULL DEFAULT 'unknown'
                                    CHECK (run_time_standard IN (
                                        'utc','local_standard_time','instrument_clock','unknown')),
    fuel_as_reported                VARCHAR(100),
    facility                        VARCHAR(100),
    composition_completeness        VARCHAR(20) NOT NULL DEFAULT 'unknown'
                                    CHECK (composition_completeness IN (
                                        'complete','partial','unknown','not_reported')),
    gravity_regime                  VARCHAR(50) NOT NULL DEFAULT 'unknown'
                                    CHECK (gravity_regime IN (
                                        'microgravity','partial_gravity','1g','hypergravity','unknown')),
    gravity_information_source      VARCHAR(100),
    gravity_reference_frame         VARCHAR(100),
    gravity_direction               VARCHAR(100),
    gravity_time_variation          VARCHAR(100),
    gravity_regime_uncertainty      VARCHAR(100),
    gravity_acceleration_ms2        REAL CHECK (gravity_acceleration_ms2 IS NULL OR gravity_acceleration_ms2 >= 0),
    gravity_acceleration_uncertainty_ms2 REAL
                                    CHECK (gravity_acceleration_uncertainty_ms2 IS NULL
                                        OR gravity_acceleration_uncertainty_ms2 >= 0),
    pressure                        REAL CHECK (pressure IS NULL OR pressure >= 0),
    pressure_unit                   VARCHAR(20) CHECK (pressure_unit IS NULL OR pressure_unit IN (
        'kpa','pa','mpa','psi','bar','atm','torr','other')),
    pressure_uncertainty            REAL CHECK (pressure_uncertainty IS NULL OR pressure_uncertainty >= 0),
    pressure_interval_low           REAL CHECK (pressure_interval_low IS NULL OR pressure_interval_low >= 0),
    pressure_interval_high          REAL CHECK (pressure_interval_high IS NULL OR pressure_interval_high >= 0),
    temperature                     REAL,
    temperature_unit                VARCHAR(20) CHECK (temperature_unit IS NULL OR temperature_unit IN (
        'k','degc','degf','other')),
    temperature_uncertainty         REAL CHECK (temperature_uncertainty IS NULL OR temperature_uncertainty >= 0),
    temperature_approx              INTEGER NOT NULL DEFAULT 0 CHECK (temperature_approx IN (0,1)),
    flow_velocity                   REAL CHECK (flow_velocity IS NULL OR flow_velocity >= 0),
    flow_velocity_unit              VARCHAR(20) CHECK (flow_velocity_unit IS NULL OR flow_velocity_unit IN (
        'm_per_s','cm_per_s','mm_per_s','other')),
    flow_velocity_uncertainty       REAL CHECK (flow_velocity_uncertainty IS NULL OR flow_velocity_uncertainty >= 0),
    flow_velocity_approx            INTEGER NOT NULL DEFAULT 0 CHECK (flow_velocity_approx IN (0,1)),
    duration                        REAL CHECK (duration IS NULL OR duration >= 0),
    duration_unit                   VARCHAR(20) CHECK (duration_unit IS NULL OR duration_unit IN (
        's','ms','us','ns','min','other')),
    duration_uncertainty            REAL CHECK (duration_uncertainty IS NULL OR duration_uncertainty >= 0),
    notes                           TEXT,
    CHECK (pressure_interval_low IS NULL OR pressure_interval_high IS NULL
           OR pressure_interval_low <= pressure_interval_high),
    -- Unit required whenever ANY pressure quantity (value, uncertainty, or
    -- interval bound) is present; uncertainty shares that unit.
    CHECK (
        (
            pressure IS NULL
            AND pressure_uncertainty IS NULL
            AND pressure_interval_low IS NULL
            AND pressure_interval_high IS NULL
        )
        OR pressure_unit IS NOT NULL
    ),
    CHECK (temperature IS NULL OR temperature_unit IS NOT NULL),
    CHECK (temperature_uncertainty IS NULL
           OR (temperature IS NOT NULL AND temperature_unit IS NOT NULL)),
    CHECK (flow_velocity IS NULL OR flow_velocity_unit IS NOT NULL),
    CHECK (flow_velocity_uncertainty IS NULL
           OR (flow_velocity IS NOT NULL AND flow_velocity_unit IS NOT NULL)),
    CHECK (duration IS NULL OR duration_unit IS NOT NULL),
    UNIQUE (experiment_id, run_label)
);

-- ----------------------------------------------------------------------------
-- 9. run_composition (mole/mass bases are independent by design; no auto
--    conversion. Sum-to-one is validated at ingestion when
--    composition_completeness = 'complete'.)
-- ----------------------------------------------------------------------------
CREATE TABLE run_composition (
    run_composition_id      TEXT PRIMARY KEY,
    run_id                  TEXT NOT NULL REFERENCES experimental_run(run_id),
    species_id              TEXT NOT NULL REFERENCES chemical_species(species_id),
    role                    VARCHAR(50) NOT NULL CHECK (role IN (
        'fuel','oxidizer','diluent','suppressant','inert')),
    mole_fraction           REAL CHECK (mole_fraction IS NULL OR (mole_fraction >= 0.0 AND mole_fraction <= 1.0)),
    mole_fraction_uncertainty REAL CHECK (mole_fraction_uncertainty IS NULL OR mole_fraction_uncertainty >= 0.0),
    mole_fraction_approx    INTEGER NOT NULL DEFAULT 0 CHECK (mole_fraction_approx IN (0,1)),
    mass_fraction           REAL CHECK (mass_fraction IS NULL OR (mass_fraction >= 0.0 AND mass_fraction <= 1.0)),
    mass_fraction_uncertainty REAL CHECK (mass_fraction_uncertainty IS NULL OR mass_fraction_uncertainty >= 0.0),
    mass_fraction_approx    INTEGER NOT NULL DEFAULT 0 CHECK (mass_fraction_approx IN (0,1)),
    notes                   TEXT,
    UNIQUE (run_id, species_id, role),
    CHECK (mole_fraction_uncertainty IS NULL OR mole_fraction IS NOT NULL),
    CHECK (mole_fraction_approx = 0 OR mole_fraction IS NOT NULL),
    CHECK (mass_fraction_uncertainty IS NULL OR mass_fraction IS NOT NULL),
    CHECK (mass_fraction_approx = 0 OR mass_fraction IS NOT NULL)
);

-- ----------------------------------------------------------------------------
-- 10. droplet_geometry
-- ----------------------------------------------------------------------------
CREATE TABLE droplet_geometry (
    droplet_geometry_id     TEXT PRIMARY KEY,
    run_id                  TEXT NOT NULL UNIQUE REFERENCES experimental_run(run_id),
    initial_diameter        REAL CHECK (initial_diameter IS NULL OR initial_diameter > 0),
    initial_diameter_unit   VARCHAR(20) NOT NULL DEFAULT 'mm'
                            CHECK (initial_diameter_unit IN ('mm','um','m','cm','other')),
    initial_diameter_uncertainty REAL
                            CHECK (initial_diameter_uncertainty IS NULL OR initial_diameter_uncertainty >= 0),
    initial_diameter_approx INTEGER NOT NULL DEFAULT 0 CHECK (initial_diameter_approx IN (0,1)),
    support_fiber           INTEGER NOT NULL DEFAULT 0 CHECK (support_fiber IN (0,1)),
    fiber_material          VARCHAR(100),
    fiber_diameter          REAL CHECK (fiber_diameter IS NULL OR fiber_diameter > 0),
    fiber_diameter_unit     VARCHAR(20) CHECK (fiber_diameter_unit IN ('mm','um','m','cm','other')),
    fiber_diameter_uncertainty REAL
                            CHECK (fiber_diameter_uncertainty IS NULL OR fiber_diameter_uncertainty >= 0),
    orientation             VARCHAR(50),
    deployment_method       VARCHAR(100),
    notes                   TEXT,
    CHECK (support_fiber = 1 OR fiber_material IS NULL),
    CHECK (support_fiber = 1 OR fiber_diameter IS NULL),
    CHECK (support_fiber = 1 OR fiber_diameter_unit IS NULL),
    CHECK (support_fiber = 1 OR fiber_diameter_uncertainty IS NULL),
    CHECK (fiber_diameter IS NULL OR fiber_diameter_unit IS NOT NULL),
    CHECK (initial_diameter_uncertainty IS NULL OR initial_diameter IS NOT NULL),
    CHECK (initial_diameter_approx = 0 OR initial_diameter IS NOT NULL),
    CHECK (fiber_diameter_uncertainty IS NULL OR fiber_diameter IS NOT NULL)
);

-- ----------------------------------------------------------------------------
-- 11. solid_fuel_geometry
-- ----------------------------------------------------------------------------
CREATE TABLE solid_fuel_geometry (
    solid_fuel_geometry_id  TEXT PRIMARY KEY,
    run_id                  TEXT NOT NULL UNIQUE REFERENCES experimental_run(run_id),
    fuel_form               VARCHAR(100) NOT NULL CHECK (fuel_form IN (
        'flat_sheet','thin_film','rod','cylinder','powder_bed')),
    thickness               REAL CHECK (thickness IS NULL OR thickness > 0),
    thickness_unit          VARCHAR(20) NOT NULL
                            CHECK (thickness_unit IN ('mm','um','m','cm','other')),
    thickness_uncertainty   REAL CHECK (thickness_uncertainty IS NULL OR thickness_uncertainty >= 0),
    width                   REAL CHECK (width IS NULL OR width > 0),
    width_unit              VARCHAR(20) CHECK (width_unit IN ('mm','um','m','cm','other')),
    width_uncertainty       REAL CHECK (width_uncertainty IS NULL OR width_uncertainty >= 0),
    length                  REAL CHECK (length IS NULL OR length > 0),
    length_unit             VARCHAR(20) CHECK (length_unit IN ('mm','um','m','cm','other')),
    length_uncertainty      REAL CHECK (length_uncertainty IS NULL OR length_uncertainty >= 0),
    surface_area            REAL CHECK (surface_area IS NULL OR surface_area > 0),
    surface_area_unit       VARCHAR(20) CHECK (surface_area_unit IN ('mm2','um2','m2','cm2','other')),
    orientation             VARCHAR(50),
    ignition_method         VARCHAR(100),
    notes                   TEXT,
    CHECK (width IS NULL OR width_unit IS NOT NULL),
    CHECK (length IS NULL OR length_unit IS NOT NULL),
    CHECK (surface_area IS NULL OR surface_area_unit IS NOT NULL),
    CHECK (thickness_uncertainty IS NULL OR thickness IS NOT NULL),
    CHECK (width_uncertainty IS NULL OR width IS NOT NULL),
    CHECK (length_uncertainty IS NULL OR length IS NOT NULL)
);

-- ----------------------------------------------------------------------------
-- 12. event
-- Original reported time text is preserved verbatim (event_time_original);
-- no automatic clock correction is applied. An anchor event normally has
-- time_reference_id = NULL; an interpreted event points at a time_reference.
-- ----------------------------------------------------------------------------
CREATE TABLE event (
    event_id                TEXT PRIMARY KEY,
    run_id                  TEXT NOT NULL REFERENCES experimental_run(run_id),
    event_type              VARCHAR(50) NOT NULL CHECK (event_type IN (
        'ignition','burn_out','end_of_test','point_injection','soot_onset','flame_spread',
        'oxygen_depletion','partial_gravity_onset','partial_gravity_offset','relocating',
        'sample_acquisition','other')),
    event_label             TEXT,
    time_base               VARCHAR(30) NOT NULL CHECK (time_base IN (
        'absolute_datetime','run_relative_seconds','frame_index','clock_domain_time','unknown')),
    clock_domain_id         TEXT REFERENCES clock_domain(clock_domain_id),
    time_reference_id       TEXT,
    event_time_original     TEXT,
    event_time_original_format VARCHAR(50),
    event_datetime_start    TEXT,
    event_datetime_end      TEXT,
    event_relative_start_s  REAL,
    event_relative_end_s    REAL,
    event_frame_start       INTEGER CHECK (event_frame_start IS NULL OR event_frame_start >= 0),
    event_frame_end         INTEGER CHECK (event_frame_end IS NULL OR event_frame_end >= 0),
    event_domain_time_start REAL,
    event_domain_time_end   REAL,
    duration_s              REAL CHECK (duration_s IS NULL OR duration_s >= 0),
    duration_uncertainty_s  REAL CHECK (duration_uncertainty_s IS NULL OR duration_uncertainty_s >= 0),
    notes                   TEXT,
    CHECK (event_frame_start IS NULL OR event_frame_end IS NULL OR event_frame_start <= event_frame_end),
    CHECK (event_relative_start_s IS NULL OR event_relative_end_s IS NULL
           OR event_relative_start_s <= event_relative_end_s),
    CHECK (event_datetime_start IS NULL OR event_datetime_end IS NULL
           OR event_datetime_start <= event_datetime_end),
    CHECK (event_domain_time_start IS NULL OR event_domain_time_end IS NULL
           OR event_domain_time_start <= event_domain_time_end),
    CHECK (event_datetime_end IS NULL OR event_datetime_start IS NOT NULL),
    CHECK (event_relative_end_s IS NULL OR event_relative_start_s IS NOT NULL),
    CHECK (event_frame_end IS NULL OR event_frame_start IS NOT NULL),
    CHECK (event_domain_time_end IS NULL OR event_domain_time_start IS NOT NULL),
    -- Exactly one representation family (start AND end fields) may be populated,
    -- and it must match the declared time_base. Cross-base contamination is rejected.
    CONSTRAINT chk_event_time_base CHECK (
        CASE time_base
            WHEN 'absolute_datetime' THEN event_datetime_start IS NOT NULL
                AND event_relative_start_s IS NULL AND event_relative_end_s IS NULL
                AND event_frame_start IS NULL AND event_frame_end IS NULL
                AND event_domain_time_start IS NULL AND event_domain_time_end IS NULL
                AND clock_domain_id IS NULL
            WHEN 'run_relative_seconds' THEN event_relative_start_s IS NOT NULL
                AND event_datetime_start IS NULL AND event_datetime_end IS NULL
                AND event_frame_start IS NULL AND event_frame_end IS NULL
                AND event_domain_time_start IS NULL AND event_domain_time_end IS NULL
                AND clock_domain_id IS NULL
            WHEN 'frame_index' THEN event_frame_start IS NOT NULL
                AND event_datetime_start IS NULL AND event_datetime_end IS NULL
                AND event_relative_start_s IS NULL AND event_relative_end_s IS NULL
                AND event_domain_time_start IS NULL AND event_domain_time_end IS NULL
                AND clock_domain_id IS NULL
            WHEN 'clock_domain_time' THEN event_domain_time_start IS NOT NULL
                AND clock_domain_id IS NOT NULL
                AND event_datetime_start IS NULL AND event_datetime_end IS NULL
                AND event_relative_start_s IS NULL AND event_relative_end_s IS NULL
                AND event_frame_start IS NULL AND event_frame_end IS NULL
            WHEN 'unknown' THEN event_datetime_start IS NULL AND event_datetime_end IS NULL
                AND event_relative_start_s IS NULL AND event_relative_end_s IS NULL
                AND event_frame_start IS NULL AND event_frame_end IS NULL
                AND event_domain_time_start IS NULL AND event_domain_time_end IS NULL
                AND clock_domain_id IS NULL
        END
    ),
    UNIQUE (run_id, event_id),
    FOREIGN KEY (run_id, time_reference_id)
        REFERENCES time_reference (run_id, time_reference_id)
);

-- ----------------------------------------------------------------------------
-- 13. time_reference
-- reference_offset_s: signed seconds from the anchor instant to the instant
-- this reference designates (event anchor -> anchor event's interpreted start
-- instant; absolute -> reference_absolute_time; numeric -> no epoch guarantee,
-- so an offset is forbidden).
-- For reference_kind='numeric', reference_numeric_value is expressed in
-- reference_numeric_unit within clock_domain_id when one is supplied; otherwise
-- it is an unanchored numeric reference. The unit alone never implies UTC or
-- run-relative meaning.
-- ----------------------------------------------------------------------------
CREATE TABLE time_reference (
    time_reference_id     TEXT PRIMARY KEY,
    run_id                TEXT NOT NULL REFERENCES experimental_run(run_id),
    reference_label       VARCHAR(100) NOT NULL,
    reference_kind        VARCHAR(20) NOT NULL CHECK (reference_kind IN (
        'event','absolute','numeric','unknown')),
    reference_event_id    TEXT,
    reference_absolute_time TEXT,
    absolute_time_statement VARCHAR(30) CHECK (absolute_time_statement IS NULL
        OR absolute_time_statement IN (
            'utc','local_standard_time','instrument_clock','locale_declared_elsewhere','unknown')),
    reference_numeric_value REAL,
    reference_numeric_unit VARCHAR(20) CHECK (reference_numeric_unit IS NULL
        OR reference_numeric_unit IN ('s','ms','us','ns','min','frame','count')),
    reference_numeric_uncertainty REAL
        CHECK (reference_numeric_uncertainty IS NULL OR reference_numeric_uncertainty >= 0),
    reference_offset_s    REAL,
    reference_offset_uncertainty_s REAL
        CHECK (reference_offset_uncertainty_s IS NULL OR reference_offset_uncertainty_s >= 0),
    clock_domain_id       TEXT REFERENCES clock_domain(clock_domain_id),
    established_at        TEXT NOT NULL DEFAULT (datetime('now')),
    notes                 TEXT,
    CHECK (reference_kind = 'event' OR reference_event_id IS NULL),
    CHECK (reference_kind = 'absolute'
           OR (reference_absolute_time IS NULL AND absolute_time_statement IS NULL)),
    CHECK (reference_kind = 'numeric'
           OR (reference_numeric_value IS NULL AND reference_numeric_unit IS NULL
               AND reference_numeric_uncertainty IS NULL)),
    CHECK (reference_kind IN ('event','absolute')
           OR (reference_offset_s IS NULL AND reference_offset_uncertainty_s IS NULL)),
    CHECK (reference_kind <> 'numeric'
           OR (reference_numeric_value IS NOT NULL AND reference_numeric_unit IS NOT NULL)),
    CHECK (reference_offset_uncertainty_s IS NULL OR reference_offset_s IS NOT NULL),
    -- An absolute anchor must be an ISO 8601 date-time; a date alone is not an instant.
    CHECK (reference_absolute_time IS NULL
           OR reference_absolute_time GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*'),
    CONSTRAINT chk_time_reference_kind CHECK (
        CASE reference_kind
            WHEN 'event'    THEN reference_event_id IS NOT NULL
                               AND reference_absolute_time IS NULL
                               AND absolute_time_statement IS NULL
                               AND reference_numeric_value IS NULL
                               AND reference_numeric_unit IS NULL
                               AND reference_numeric_uncertainty IS NULL
            WHEN 'absolute' THEN reference_absolute_time IS NOT NULL
                               AND absolute_time_statement IS NOT NULL
                               AND reference_event_id IS NULL
                               AND reference_numeric_value IS NULL
                               AND reference_numeric_unit IS NULL
                               AND reference_numeric_uncertainty IS NULL
            WHEN 'numeric'  THEN reference_numeric_value IS NOT NULL
                               AND reference_numeric_unit IS NOT NULL
                               AND reference_event_id IS NULL
                               AND reference_absolute_time IS NULL
                               AND reference_offset_s IS NULL
                               AND reference_offset_uncertainty_s IS NULL
            WHEN 'unknown'  THEN reference_event_id IS NULL
                               AND reference_absolute_time IS NULL
                               AND absolute_time_statement IS NULL
                               AND reference_numeric_value IS NULL
                               AND reference_numeric_unit IS NULL
                               AND reference_numeric_uncertainty IS NULL
                               AND reference_offset_s IS NULL
                               AND reference_offset_uncertainty_s IS NULL
                               AND clock_domain_id IS NULL
        END
    ),
    FOREIGN KEY (run_id, reference_event_id) REFERENCES event (run_id, event_id),
    UNIQUE (run_id, time_reference_id)
);

-- ----------------------------------------------------------------------------
-- 14. clock_sync
-- Directional convention: t_target = t_source + offset_seconds
-- sync_status semantics:
--   established  validated offset + method for the stated validity interval
--   inferred     offset derived by reasoning (offset required)
--   assumed      relationship known, value may be unknown (offset optional)
--   invalidated  previously claimed sync disproven (notes required)
--   unknown      synchronization relationship known but completely
--                uncharacterized (offset AND method must be NULL)
-- sync_segment_id identifies a calibration segment within
-- (run, source_domain, target_domain); it closes SQLite's NULL-distinct
-- UNIQUE gap so distinct segments always coexist. Interval overlap detection
-- is an ingestion-level validation, not a schema constraint.
-- ----------------------------------------------------------------------------
CREATE TABLE clock_sync (
    clock_sync_id             TEXT PRIMARY KEY,
    run_id                    TEXT NOT NULL REFERENCES experimental_run(run_id),
    source_domain_id          TEXT NOT NULL REFERENCES clock_domain(clock_domain_id),
    target_domain_id          TEXT NOT NULL REFERENCES clock_domain(clock_domain_id),
    sync_segment_id           INTEGER NOT NULL CHECK (sync_segment_id >= 0),
    offset_seconds            REAL,
    offset_uncertainty_seconds REAL
        CHECK (offset_uncertainty_seconds IS NULL OR offset_uncertainty_seconds >= 0),
    sync_status               VARCHAR(20) NOT NULL CHECK (sync_status IN (
        'established','inferred','assumed','invalidated','unknown')),
    sync_method               VARCHAR(100),
    sync_reference_time       TEXT,
    valid_from                TEXT,
    valid_to                  TEXT,
    notes                     TEXT,
    CHECK (source_domain_id <> target_domain_id),
    CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to),
    CHECK (sync_status <> 'established'
           OR (offset_seconds IS NOT NULL AND sync_method IS NOT NULL)),
    CHECK (sync_status <> 'inferred' OR offset_seconds IS NOT NULL),
    CHECK (sync_status <> 'invalidated' OR notes IS NOT NULL),
    CHECK (sync_status <> 'unknown'
           OR (offset_seconds IS NULL AND sync_method IS NULL)),
    UNIQUE (run_id, source_domain_id, target_domain_id, sync_segment_id)
);

-- ----------------------------------------------------------------------------
-- 15. measurement
-- ----------------------------------------------------------------------------
CREATE TABLE measurement (
    measurement_id           TEXT PRIMARY KEY,
    run_id                   TEXT NOT NULL REFERENCES experimental_run(run_id),
    measurement_name         VARCHAR(200) NOT NULL,
    measurement_kind         VARCHAR(50) NOT NULL CHECK (measurement_kind IN (
        'ignition_delay','burn_time','flame_spread_rate','soot_volume_fraction',
        'droplet_diameter','gas_concentration','oxygen_concentration','flame_temperature',
        'heat_flux','flame_height','normalized_burning_rate','thermophoretic_sampling',
        'flame_standoff_distance','other')),
    measurement_method       VARCHAR(100),
    measurement_domain       VARCHAR(50) NOT NULL CHECK (measurement_domain IN (
        'image_diagnostic','gas_analysis','thermocouple','xray_imaging','light_emission',
        'plasma_emission','laser_diagnostic','pressure_transducer','recorded_log','other')),
    clock_domain_id          TEXT REFERENCES clock_domain(clock_domain_id),
    time_reference_id        TEXT,
    normalizes_run_timeline  INTEGER NOT NULL DEFAULT 0 CHECK (normalizes_run_timeline IN (0,1)),
    is_key_measurement       INTEGER NOT NULL DEFAULT 0 CHECK (is_key_measurement IN (0,1)),
    detection_limit          REAL CHECK (detection_limit IS NULL OR detection_limit >= 0),
    detection_limit_unit     VARCHAR(20),
    measurement_unit         VARCHAR(20),
    measurement_approx       INTEGER NOT NULL DEFAULT 0 CHECK (measurement_approx IN (0,1)),
    notes                    TEXT,
    CHECK (detection_limit IS NULL OR detection_limit_unit IS NOT NULL),
    CHECK (normalizes_run_timeline = 0 OR time_reference_id IS NOT NULL),
    FOREIGN KEY (run_id, time_reference_id)
        REFERENCES time_reference (run_id, time_reference_id)
);

-- ----------------------------------------------------------------------------
-- 16. measurement_channel
-- Conversion is affine y = scale*x + offset; offset-only conversion is not
-- supported, so conversion_offset requires conversion_scale.
-- sampling_interval_s is standardized to seconds. sampling_frequency_actual
-- uses sampling_frequency_unit (same unit as sampling_frequency). Frequency/
-- interval mathematical consistency is validated at ingestion with a stated
-- tolerance; the schema does not imply it.
-- ----------------------------------------------------------------------------
CREATE TABLE measurement_channel (
    measurement_channel_id       TEXT PRIMARY KEY,
    measurement_id               TEXT NOT NULL REFERENCES measurement(measurement_id),
    channel_name                 VARCHAR(100) NOT NULL,
    channel_role                 VARCHAR(100),
    channel_index                INTEGER CHECK (channel_index IS NULL OR channel_index >= 0),
    channel_domain               VARCHAR(50),
    physical_quantity            VARCHAR(100),
    quantity_unit_parsed         VARCHAR(20),
    sensor_type                  VARCHAR(100),
    sampling_frequency           REAL CHECK (sampling_frequency IS NULL OR sampling_frequency > 0),
    sampling_frequency_actual    REAL CHECK (sampling_frequency_actual IS NULL OR sampling_frequency_actual > 0),
    sampling_frequency_unit      VARCHAR(20) NOT NULL DEFAULT 'Hz'
                                  CHECK (sampling_frequency_unit IN ('Hz','kHz','fps')),
    sampling_interval_s          REAL CHECK (sampling_interval_s IS NULL OR sampling_interval_s > 0),
    aggregate_duration           REAL CHECK (aggregate_duration IS NULL OR aggregate_duration >= 0),
    duration_uncertainty         REAL CHECK (duration_uncertainty IS NULL OR duration_uncertainty >= 0),
    aggregation_window           REAL CHECK (aggregation_window IS NULL OR aggregation_window > 0),
    conversion_scale             REAL CHECK (conversion_scale IS NULL OR conversion_scale <> 0),
    conversion_offset            REAL,
    conversion_unit              VARCHAR(20),
    conversion_uncertainty       REAL CHECK (conversion_uncertainty IS NULL OR conversion_uncertainty >= 0),
    raw_original_values          TEXT,
    raw_value_representation     VARCHAR(50),
    unified_raw_numeric_values   TEXT,
    unified_value_unit           VARCHAR(20),
    original_raw_unit            VARCHAR(20),
    notes                        TEXT,
    UNIQUE (measurement_id, channel_name),
    CHECK (physical_quantity IS NULL OR quantity_unit_parsed IS NOT NULL),
    CHECK (conversion_scale IS NULL OR conversion_unit IS NOT NULL),
    CHECK (conversion_offset IS NULL OR conversion_scale IS NOT NULL)
);

-- ----------------------------------------------------------------------------
-- 17. measurement_sample
-- Identity is (channel_id, sample_index): FLEX time series repeat identical
-- timestamps.
-- original_timestamp_parsed = source-native numeric value in the SOURCE
--   representation (Excel serial, LabVIEW timestamp, microseconds since start,
--   frame index, ...). No epoch bound: its range depends on the representation.
-- timestamp_epoch_utc       = normalized UTC epoch seconds (UTC), populated
--   only when parsing succeeded and the representation is unambiguously
--   convertible to UTC. Conservative policy: run_relative_seconds and
--   frame_number are NOT directly epoch-convertible without the reference
--   chain (validated at ingestion).
-- ----------------------------------------------------------------------------
CREATE TABLE measurement_sample (
    measurement_sample_id        TEXT PRIMARY KEY,
    measurement_channel_id       TEXT NOT NULL REFERENCES measurement_channel(measurement_channel_id),
    sample_index                 INTEGER NOT NULL CHECK (sample_index >= 0),
    original_timestamp           TEXT,
    timestamp_parsing_status     VARCHAR(20) NOT NULL CHECK (timestamp_parsing_status IN (
        'parsed','unparsed','ambiguous','failed','unknown')),
    parsed_time_format           VARCHAR(50),
    timestamp_representation     VARCHAR(50) NOT NULL CHECK (timestamp_representation IN (
        'iso8601_datetime','excel_serial_number','unix_time','run_relative_seconds','frame_number',
        'labview_timestamp','microseconds_since_start','date_only','time_only','free_text_number',
        'unknown_representation')),
    original_timestamp_parsed    REAL,
    timestamp_epoch_utc          REAL,
    run_relative_s               REAL,
    original_value               TEXT,
    original_value_parsed        REAL,
    value_representation         VARCHAR(50) NOT NULL CHECK (value_representation IN (
        'integer','float','scientific_notation','thousands_separator','numerical_range',
        'european_decimal_comma','unit_text','english_text','qualitative','multi_value',
        'average','coded','unknown_representation')),
    normalized_value             REAL,
    normalized_unit              VARCHAR(20),
    normalization_method         VARCHAR(100),
    normalization_version        VARCHAR(50),
    normalization_notes          TEXT,
    value_status                 VARCHAR(30) NOT NULL CHECK (value_status IN (
        'valid_numeric','valid_qualitative','valid_coded','missing','invalid','outlier',
        'censored','below_detection_limit','above_saturation_limit')),
    quality_flag                 VARCHAR(50) CHECK (
        quality_flag IS NULL OR quality_flag IN (
            'ok','saturated','outlier','contaminated','interpolated','repeated','estimated','suspect')),
    quality_flag_original        TEXT,
    detection_limit_applied      VARCHAR(20) NOT NULL DEFAULT 'none'
                                  CHECK (detection_limit_applied IN ('none','below','above','censored')),
    detection_limit_value        REAL CHECK (detection_limit_value IS NULL OR detection_limit_value >= 0),
    detection_limit_unit         VARCHAR(20),
    coded_value_system           VARCHAR(100),
    conversion_scale             REAL CHECK (conversion_scale IS NULL OR conversion_scale <> 0),
    conversion_unit              VARCHAR(20),
    normalized_uncertainty       REAL CHECK (normalized_uncertainty IS NULL OR normalized_uncertainty >= 0),
    capture_mode                 VARCHAR(30) NOT NULL DEFAULT 'continuous'
                                  CHECK (capture_mode IN (
                                      'continuous','discrete','triggered','derived','manual_pick')),
    capture_condition            VARCHAR(30) NOT NULL DEFAULT 'discrete_sample'
                                  CHECK (capture_condition IN (
                                      'discrete_sample','continuous_record','triggered_event',
                                      'post_ignition','pre_ignition','flame_present','flame_absent',
                                      'soot_present','soot_absent','image_frame_viewer_comment')),
    capture_condition_original   TEXT,
    notes                        TEXT,
    UNIQUE (measurement_channel_id, sample_index),
    CHECK (detection_limit_value IS NULL OR detection_limit_unit IS NOT NULL),
    -- unknown_representation preserves a raw timestamp string whose format is
    -- not identifiable; parsed and epoch fields stay NULL.
    CHECK (
        (timestamp_representation = 'unknown_representation'
         AND timestamp_parsing_status = 'unknown'
         AND original_timestamp_parsed IS NULL
         AND timestamp_epoch_utc IS NULL)
        OR timestamp_representation <> 'unknown_representation'),
    -- epoch only from a parsed, convertible representation (conservative policy).
    CHECK (
        timestamp_epoch_utc IS NULL
        OR (timestamp_parsing_status = 'parsed'
            AND timestamp_representation IN (
                'iso8601_datetime','unix_time','excel_serial_number','labview_timestamp'))),
    -- Domain sanity window (1900-2100) on the NORMALIZED epoch only.
    CHECK (timestamp_epoch_utc IS NULL
           OR (timestamp_epoch_utc >= -2208988800 AND timestamp_epoch_utc < 4102444800)),
    -- ambiguous: a source-native number may be read, but its basis/timezone is
    -- not interpretable, so the normalized epoch must remain NULL.
    CHECK (
        timestamp_parsing_status <> 'ambiguous'
        OR timestamp_epoch_utc IS NULL),
    CONSTRAINT chk_sample_timestamp_consistency CHECK (
        CASE timestamp_parsing_status
            WHEN 'parsed'    THEN original_timestamp IS NOT NULL
                                 AND timestamp_representation <> 'unknown_representation'
                                 AND parsed_time_format IS NOT NULL
                                 AND (
                                     timestamp_representation = 'iso8601_datetime'
                                     OR original_timestamp_parsed IS NOT NULL
                                 )
            WHEN 'unparsed'  THEN original_timestamp IS NOT NULL
                                 AND original_timestamp_parsed IS NULL
                                 AND timestamp_representation <> 'unknown_representation'
            WHEN 'ambiguous' THEN original_timestamp IS NOT NULL
                                 AND timestamp_representation <> 'unknown_representation'
            WHEN 'failed'    THEN original_timestamp IS NOT NULL
                                 AND original_timestamp_parsed IS NULL
            WHEN 'unknown'   THEN original_timestamp_parsed IS NULL
                                 AND (
                                     (timestamp_representation = 'unknown_representation'
                                      AND original_timestamp IS NOT NULL)
                                     OR
                                     (timestamp_representation <> 'unknown_representation'
                                      AND original_timestamp IS NULL)
                                 )
        END
    ),
    CONSTRAINT chk_sample_value_consistency CHECK (
        CASE value_status
            WHEN 'valid_numeric'        THEN original_value IS NOT NULL
                                           AND original_value_parsed IS NOT NULL
                                           AND detection_limit_applied = 'none'
                                           AND (quality_flag IS NULL OR quality_flag = 'ok')
                                           AND value_representation IN (
                                               'integer','float','scientific_notation',
                                               'thousands_separator','numerical_range',
                                               'european_decimal_comma','average')
            WHEN 'valid_qualitative'    THEN original_value IS NOT NULL
                                           AND original_value_parsed IS NULL
                                           AND normalized_value IS NULL
                                           AND detection_limit_applied = 'none'
                                           AND value_representation IN ('qualitative','english_text')
            WHEN 'valid_coded'          THEN original_value IS NOT NULL
                                           AND original_value_parsed IS NULL
                                           AND normalized_value IS NULL
                                           AND detection_limit_applied = 'none'
                                           AND value_representation = 'coded'
                                           AND coded_value_system IS NOT NULL
            WHEN 'missing'              THEN original_value IS NULL
                                           AND original_value_parsed IS NULL
                                           AND normalized_value IS NULL
                                           AND capture_condition = 'discrete_sample'
                                           AND capture_condition_original IS NULL
            WHEN 'invalid'              THEN quality_flag IS NOT NULL AND quality_flag <> 'ok'
            WHEN 'outlier'              THEN quality_flag = 'outlier'
                                           AND original_value_parsed IS NOT NULL
            WHEN 'censored'             THEN detection_limit_applied = 'censored'
                                           AND detection_limit_value IS NOT NULL
                                           AND detection_limit_unit IS NOT NULL
            WHEN 'below_detection_limit' THEN detection_limit_applied = 'below'
                                           AND detection_limit_value IS NOT NULL
                                           AND detection_limit_unit IS NOT NULL
                                           AND (original_value_parsed IS NOT NULL
                                                OR original_value IS NOT NULL)
            WHEN 'above_saturation_limit' THEN detection_limit_applied = 'above'
                                           AND detection_limit_value IS NOT NULL
                                           AND detection_limit_unit IS NOT NULL
        END
    ),
    CONSTRAINT chk_sample_text_representation CHECK (
        value_representation NOT IN ('unit_text','english_text','qualitative','multi_value',
                                     'unknown_representation')
        OR value_status NOT IN ('valid_numeric','valid_coded')
    ),
    CONSTRAINT chk_sample_normalization_traceability CHECK (
        normalized_value IS NULL
        OR (normalization_method IS NOT NULL AND normalized_unit IS NOT NULL)
    )
);

-- ----------------------------------------------------------------------------
-- 18. file_run_reference
-- ----------------------------------------------------------------------------
CREATE TABLE file_run_reference (
    file_run_reference_id TEXT PRIMARY KEY,
    file_id               TEXT NOT NULL REFERENCES data_file(file_id),
    run_id                TEXT NOT NULL REFERENCES experimental_run(run_id),
    reference_role        VARCHAR(30) NOT NULL CHECK (reference_role IN (
        'primary_data','supplementary_data','raw_archive','processed_product')),
    description           TEXT,
    UNIQUE (file_id, run_id, reference_role)
);

-- ----------------------------------------------------------------------------
-- 19. comparability_assessment
-- Classification semantics (each requires its own evidence):
--   directly_comparable            both numeric + comparison_unit
--   comparable_after_normalization both numeric + comparison_unit + notes
--   qualitatively_comparable       both text values
--   not_comparable                 scientific justification in notes
--   insufficient_information       no evidence requirement
-- ----------------------------------------------------------------------------
CREATE TABLE comparability_assessment (
    comparability_assessment_id     TEXT PRIMARY KEY,
    run1_run_id                     TEXT NOT NULL REFERENCES experimental_run(run_id),
    run2_run_id                     TEXT NOT NULL REFERENCES experimental_run(run_id),
    measurement_subject             VARCHAR(200) NOT NULL,
    gravitational_comparable        VARCHAR(20) NOT NULL
                                    CHECK (gravitational_comparable IN ('comparable','not_comparable','unknown')),
    environment_comparable          VARCHAR(20) NOT NULL
                                    CHECK (environment_comparable IN ('comparable','not_comparable','unknown')),
    measurement_method_comparable   VARCHAR(20) NOT NULL
                                    CHECK (measurement_method_comparable IN ('comparable','not_comparable','unknown')),
    data_collection_comparable      VARCHAR(20) NOT NULL
                                    CHECK (data_collection_comparable IN ('comparable','not_comparable','unknown')),
    uncertainty_overlap             VARCHAR(20) NOT NULL
                                    CHECK (uncertainty_overlap IN ('overlap','no_overlap','partial','unknown')),
    run1_value_numeric              REAL,
    run2_value_numeric              REAL,
    run1_value_text                 TEXT,
    run2_value_text                 TEXT,
    comparison_unit                 VARCHAR(20),
    comparability_classification    VARCHAR(30) NOT NULL
                                    CHECK (comparability_classification IN (
        'directly_comparable','comparable_after_normalization','qualitatively_comparable',
        'not_comparable','insufficient_information')),
    comparability_notes             TEXT,
    review_status                   VARCHAR(20) NOT NULL DEFAULT 'pending_expert_review'
                                    CHECK (review_status IN ('pending_expert_review','reviewed','disputed')),
    reviewed_by                     VARCHAR(100),
    reviewed_at                     TEXT,
    created_at                      TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (run1_run_id <> run2_run_id),
    CHECK (run1_value_numeric IS NULL OR run1_value_text IS NULL),
    CHECK (run2_value_numeric IS NULL OR run2_value_text IS NULL),
    CHECK ((run1_value_numeric IS NOT NULL OR run1_value_text IS NOT NULL)
       AND (run2_value_numeric IS NOT NULL OR run2_value_text IS NOT NULL)
       OR comparability_classification = 'insufficient_information'),
    -- Unit required whenever ANY numeric comparison value is present (D-1 fix,
    -- applied after review of the executed harness results).
    CHECK ((run1_value_numeric IS NULL AND run2_value_numeric IS NULL)
           OR comparison_unit IS NOT NULL),
    CHECK (review_status = 'pending_expert_review' OR reviewed_by IS NOT NULL),
    CONSTRAINT chk_comparability_classification CHECK (
        CASE comparability_classification
            WHEN 'directly_comparable'            THEN run1_value_numeric IS NOT NULL
                                                     AND run2_value_numeric IS NOT NULL
                                                     AND comparison_unit IS NOT NULL
            WHEN 'comparable_after_normalization' THEN run1_value_numeric IS NOT NULL
                                                     AND run2_value_numeric IS NOT NULL
                                                     AND comparison_unit IS NOT NULL
                                                     AND comparability_notes IS NOT NULL
            WHEN 'qualitatively_comparable'       THEN run1_value_text IS NOT NULL
                                                     AND run2_value_text IS NOT NULL
            WHEN 'not_comparable'                 THEN comparability_notes IS NOT NULL
            WHEN 'insufficient_information'       THEN 1
        END
    )
);

-- A reversed run order is the same comparison: reject duplicates regardless of
-- orientation. min()/max() are SQLite two-argument scalar functions (3.9.0+).
CREATE UNIQUE INDEX ux_comparability_unordered_pair
    ON comparability_assessment (measurement_subject,
                                 min(run1_run_id, run2_run_id),
                                 max(run1_run_id, run2_run_id));

-- ----------------------------------------------------------------------------
-- 20. value_provenance
-- Exactly one target column populated; provenance_type must match it.
-- curation_target_run_id is a curation aid recording which run was checked;
-- it is NOT FK-verified against the chosen target. Cross-run and cross-source
-- agreement is validated during curation.
-- ----------------------------------------------------------------------------
CREATE TABLE value_provenance (
    value_provenance_id       TEXT PRIMARY KEY,
    extraction_record_id      TEXT NOT NULL REFERENCES extraction_record(extraction_record_id),
    curation_target_run_id    TEXT REFERENCES experimental_run(run_id),
    provenance_type           VARCHAR(50) NOT NULL CHECK (provenance_type IN (
        'measurement_sample','measurement_channel','measurement','event','time_reference',
        'experimental_run','run_composition','droplet_geometry','solid_fuel_geometry',
        'comparability_assessment','experiment','source')),
    measurement_sample_id     TEXT REFERENCES measurement_sample(measurement_sample_id),
    measurement_channel_id    TEXT REFERENCES measurement_channel(measurement_channel_id),
    measurement_id            TEXT REFERENCES measurement(measurement_id),
    event_id                  TEXT REFERENCES event(event_id),
    time_reference_id         TEXT REFERENCES time_reference(time_reference_id),
    run_id                    TEXT REFERENCES experimental_run(run_id),
    run_composition_id        TEXT REFERENCES run_composition(run_composition_id),
    droplet_geometry_id       TEXT REFERENCES droplet_geometry(droplet_geometry_id),
    solid_fuel_geometry_id    TEXT REFERENCES solid_fuel_geometry(solid_fuel_geometry_id),
    comparability_assessment_id TEXT REFERENCES comparability_assessment(comparability_assessment_id),
    experiment_id             TEXT REFERENCES experiment(experiment_id),
    source_id                 TEXT REFERENCES source(source_id),
    notes                     TEXT,
    CHECK (
        (CASE WHEN measurement_sample_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN measurement_channel_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN measurement_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN event_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN time_reference_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN run_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN run_composition_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN droplet_geometry_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN solid_fuel_geometry_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN comparability_assessment_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN experiment_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN source_id IS NULL THEN 0 ELSE 1 END) = 1
    ),
    CHECK (
        (measurement_sample_id IS NOT NULL) = (provenance_type = 'measurement_sample')
    AND (measurement_channel_id IS NOT NULL) = (provenance_type = 'measurement_channel')
    AND (measurement_id IS NOT NULL) = (provenance_type = 'measurement')
    AND (event_id IS NOT NULL) = (provenance_type = 'event')
    AND (time_reference_id IS NOT NULL) = (provenance_type = 'time_reference')
    AND (run_id IS NOT NULL) = (provenance_type = 'experimental_run')
    AND (run_composition_id IS NOT NULL) = (provenance_type = 'run_composition')
    AND (droplet_geometry_id IS NOT NULL) = (provenance_type = 'droplet_geometry')
    AND (solid_fuel_geometry_id IS NOT NULL) = (provenance_type = 'solid_fuel_geometry')
    AND (comparability_assessment_id IS NOT NULL) = (provenance_type = 'comparability_assessment')
    AND (experiment_id IS NOT NULL) = (provenance_type = 'experiment')
    AND (source_id IS NOT NULL) = (provenance_type = 'source')
    )
);

-- ----------------------------------------------------------------------------
-- Self-anchor guard triggers
-- Invariant (per run): no event E and time_reference R with
--   E.time_reference_id = R.time_reference_id AND R.reference_event_id = E.event_id
-- The invariant can be violated from either side, so guards exist on both
-- tables for INSERT and UPDATE. Predicates join on run_id AND ids, matching
-- the composite foreign keys. Valid distinct-anchor use (anchor event !=
-- interpreted event) is never rejected.
-- ----------------------------------------------------------------------------

-- (A) INSERT on event: reject an event pointing at a reference already
--     anchored on this same event id (covers delete + reinsert with same id).
CREATE TRIGGER trg_event_no_self_anchor_ins
BEFORE INSERT ON event
FOR EACH ROW WHEN NEW.time_reference_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'event must not anchor itself via its time_reference')
    WHERE EXISTS (
        SELECT 1 FROM time_reference
        WHERE time_reference.run_id = NEW.run_id
          AND time_reference.time_reference_id = NEW.time_reference_id
          AND time_reference.reference_event_id = NEW.event_id
    );
END;

-- (B) UPDATE on event: reject setting time_reference_id, or changing
--     event_id / run_id while a reference is set, into a self-anchor.
--     Checks the NEW row, so id collisions with reference_event_id are caught.
CREATE TRIGGER trg_event_no_self_anchor_upd
BEFORE UPDATE ON event
FOR EACH ROW WHEN NEW.time_reference_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'event must not anchor itself via its time_reference')
    WHERE EXISTS (
        SELECT 1 FROM time_reference
        WHERE time_reference.run_id = NEW.run_id
          AND time_reference.time_reference_id = NEW.time_reference_id
          AND time_reference.reference_event_id = NEW.event_id
    );
END;

-- (C) INSERT on time_reference: reject anchoring on an event that already
--     points back at this reference id (defensive for FK-off sessions; with
--     immediate FKs enabled it is normally unreachable).
CREATE TRIGGER trg_time_reference_no_self_anchor_ins
BEFORE INSERT ON time_reference
FOR EACH ROW WHEN NEW.reference_kind = 'event' AND NEW.reference_event_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'time_reference must not be anchored on an event that references it')
    WHERE EXISTS (
        SELECT 1 FROM event
        WHERE event.run_id = NEW.run_id
          AND event.event_id = NEW.reference_event_id
          AND event.time_reference_id = NEW.time_reference_id
    );
END;

-- (D) UPDATE on time_reference: reject changing reference_event_id,
--     time_reference_id, run_id, or reference_kind into a self-anchor.
CREATE TRIGGER trg_time_reference_no_self_anchor_upd
BEFORE UPDATE ON time_reference
FOR EACH ROW WHEN NEW.reference_kind = 'event' AND NEW.reference_event_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'time_reference must not be anchored on an event that references it')
    WHERE EXISTS (
        SELECT 1 FROM event
        WHERE event.run_id = NEW.run_id
          AND event.event_id = NEW.reference_event_id
          AND event.time_reference_id = NEW.time_reference_id
    );
END;

-- ----------------------------------------------------------------------------
-- Optional geometry-exclusivity guards.
-- Enable only if a run is scientifically intended to carry exactly one fuel-
-- geometry family; otherwise the base schema permits both to coexist (an
-- application-level rule). NOT enabled by default in this candidate.
-- ----------------------------------------------------------------------------
CREATE TRIGGER trg_droplet_exclusive
BEFORE INSERT ON droplet_geometry
FOR EACH ROW WHEN EXISTS (SELECT 1 FROM solid_fuel_geometry WHERE run_id = NEW.run_id)
BEGIN
    SELECT RAISE(ABORT, 'run already has solid_fuel_geometry');
END;

CREATE TRIGGER trg_solid_exclusive
BEFORE INSERT ON solid_fuel_geometry
FOR EACH ROW WHEN EXISTS (SELECT 1 FROM droplet_geometry WHERE run_id = NEW.run_id)
BEGIN
    SELECT RAISE(ABORT, 'run already has droplet_geometry');
END;
