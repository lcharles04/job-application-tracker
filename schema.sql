-- =============================================================
-- Job Application Tracker - Database Creation Script
-- COP 4751 Course Project
--
-- Run with:  mysql -u root -p < schema.sql
-- This drops and recreates the job_tracker database, then loads
-- sample data so the app has something to show on first run.
-- =============================================================

DROP DATABASE IF EXISTS job_tracker;
CREATE DATABASE job_tracker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE job_tracker;

-- -------------------------------------------------------------
-- companies: employers the user is tracking
-- -------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_company_name UNIQUE (company_name)
);

-- -------------------------------------------------------------
-- jobs: postings at a company
-- requirements is a JSON array of skill strings, e.g.
--   ["Python", "SQL", "Flask"]
-- Deleting a company deletes its jobs (and, through jobs, the
-- applications for those jobs).
-- -------------------------------------------------------------
CREATE TABLE jobs (
    job_id       INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time','Part-time','Contract','Internship'),
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_salary_range
        CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max),
    CONSTRAINT chk_salary_positive
        CHECK ((salary_min IS NULL OR salary_min >= 0) AND (salary_max IS NULL OR salary_max >= 0))
);

-- -------------------------------------------------------------
-- applications: one application to one job
-- interview_data is a JSON array of interview rounds, e.g.
--   [{"date": "2026-10-02", "round": "Phone Screen",
--     "interviewer": "Jane Doe", "notes": "Went well"}]
-- -------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT PRIMARY KEY AUTO_INCREMENT,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn')
                      NOT NULL DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE,
    interview_data    JSON,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_applications_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- -------------------------------------------------------------
-- contacts: people at a company (recruiters, referrals, etc.)
-- -------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contacts_company
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- Indexes on foreign keys and common filters
CREATE INDEX idx_jobs_company       ON jobs(company_id);
CREATE INDEX idx_apps_job           ON applications(job_id);
CREATE INDEX idx_apps_status        ON applications(status);
CREATE INDEX idx_contacts_company   ON contacts(company_id);

-- =============================================================
-- Sample data
-- =============================================================
INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp',          'Software',       'https://www.techcorp.example',   'Miami',          'FL', 'Mid-size SaaS company. Strong intern program.'),
('DataCo',            'Analytics',      'https://www.dataco.example',     'Fort Lauderdale','FL', 'Data consulting firm. Hybrid schedule.'),
('SkyLine Aviation',  'Aerospace',      'https://www.skyline.example',    'Doral',          'FL', 'MRO provider. Looking for IT security help.'),
('SecureNet',         'Cybersecurity',  'https://www.securenet.example',  'Tampa',          'FL', 'Managed security services. SOC roles open.'),
('CloudNine Health',  'Healthcare IT',  'https://www.cloudnine.example',  'Orlando',        'FL', NULL);

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer',        'Full-time',  75000,  95000, 'https://www.techcorp.example/careers/101', '2026-09-15', JSON_ARRAY('Python', 'SQL', 'Flask')),
(2, 'Data Analyst',              'Full-time',  65000,  80000, 'https://www.dataco.example/jobs/22',       '2026-09-20', JSON_ARRAY('Python', 'SQL', 'Tableau')),
(4, 'SOC Analyst I',             'Full-time',  60000,  75000, 'https://www.securenet.example/soc',        '2026-10-01', JSON_ARRAY('SIEM', 'Linux', 'Networking', 'Incident Response')),
(3, 'IT Security Intern',        'Internship', 40000,  45000, 'https://www.skyline.example/intern',       '2026-10-05', JSON_ARRAY('Networking', 'Linux', 'Python')),
(5, 'Backend Engineer',          'Contract',   90000, 120000, 'https://www.cloudnine.example/backend',    '2026-10-12', JSON_ARRAY('Python', 'Flask', 'MySQL', 'Docker', 'AWS')),
(1, 'QA Automation Engineer',    'Part-time',  35000,  50000, NULL,                                       '2026-10-20', JSON_ARRAY('Python', 'Selenium', 'Git'));

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-09-18', 'Interview', 'v3-software', TRUE,
    JSON_ARRAY(
        JSON_OBJECT('date', '2026-09-30', 'round', 'Phone Screen', 'interviewer', 'Maria Lopez', 'notes', 'Asked about Flask projects'),
        JSON_OBJECT('date', '2026-10-10', 'round', 'Technical',    'interviewer', 'Dev Team',    'notes', 'SQL joins and a live coding task'),
        -- dated relative to today so the dashboard always shows an upcoming interview
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() + INTERVAL 7 DAY, '%Y-%m-%d'),
                    'round', 'Final Round', 'interviewer', 'VP Engineering', 'notes', 'Prepare system design examples')
    )),
(2, '2026-09-22', 'Screening', 'v2-data',     FALSE, JSON_ARRAY()),
(3, '2026-10-03', 'Applied',   'v3-security', TRUE,  JSON_ARRAY()),
(4, '2026-10-06', 'Offer',     'v3-security', TRUE,
    JSON_ARRAY(
        JSON_OBJECT('date', '2026-10-15', 'round', 'Panel', 'interviewer', 'Kevin Brooks', 'notes', 'Offer extended Oct 20')
    )),
(6, '2026-10-22', 'Rejected',  'v1-general',  FALSE, JSON_ARRAY());

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Maria Lopez',   'Technical Recruiter',   'maria.lopez@techcorp.example', '305-555-0142', 'https://www.linkedin.com/in/example-maria', 'Met at FIU career fair'),
(2, 'James Carter',  'Hiring Manager',        'jcarter@dataco.example',       '954-555-0199', NULL,                                       'Referral from NSBE alum'),
(3, 'Kevin Brooks',  'IT Director',           'kbrooks@skyline.example',      '786-555-0110', 'https://www.linkedin.com/in/example-kevin', NULL),
(4, 'Aisha Grant',   'Talent Acquisition',    'agrant@securenet.example',     NULL,           NULL,                                       'Follow up in two weeks');
