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
-- Sample data: companies I am targeting
-- =============================================================
INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('NextEra Energy', 'Energy / Utilities', 'https://www.nexteraenergy.com', 'Juno Beach', 'FL', 'Largest utility in Florida. OT and grid security work. Close to home.'),
('Epic Systems',   'Healthcare IT',      'https://careers.epic.com',      'Verona',     'WI', 'EHR software. Relocation required. Ties to my hospital experience.'),
('Capital One',    'Financial Services', 'https://www.capitalonecareers.com', 'McLean', 'VA', 'Large cyber org and a Technology Development Program for new grads.'),
('CrowdStrike',    'Cybersecurity',      'https://www.crowdstrike.com/en-us/', 'Austin', 'TX', 'Falcon platform. Many remote roles.'),
('Data443',        'Cybersecurity',      'https://data443.com/cyren-threat-intelligence/', 'Research Triangle Park', 'NC', 'Cyren threat intelligence products.');

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Cybersecurity Analyst',              'Full-time', NULL, NULL, 'https://www.nexteraenergy.com', '2026-10-01', JSON_ARRAY('SIEM', 'Networking', 'Incident Response', 'Python', 'NERC CIP')),
(2, 'Software Developer',                 'Full-time', NULL, NULL, 'https://careers.epic.com',      '2026-09-15', JSON_ARRAY('Python', 'SQL', 'Flask')),
(3, 'Cyber Security Analyst',             'Full-time', NULL, NULL, 'https://www.capitalonecareers.com', '2026-10-10', JSON_ARRAY('Python', 'AWS', 'SQL', 'Splunk')),
(4, 'Security Operations Center Analyst', 'Full-time', NULL, NULL, 'https://www.crowdstrike.com/en-us/', '2026-10-05', JSON_ARRAY('EDR', 'Linux', 'Threat Hunting', 'Incident Response')),
(5, 'Threat Intelligence Analyst',        'Full-time', NULL, NULL, 'https://data443.com/cyren-threat-intelligence/', '2026-10-20', JSON_ARRAY('Threat Intelligence', 'Python', 'Malware Analysis', 'Networking')),
(3, 'Data Analyst',                       'Internship', NULL, NULL, 'https://www.capitalonecareers.com', '2026-09-20', JSON_ARRAY('Python', 'SQL', 'Tableau'));

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-10-03', 'Interview', 'v3-security', TRUE,
    JSON_ARRAY(
        JSON_OBJECT('date', '2026-10-15', 'round', 'Phone Screen', 'interviewer', 'Recruiter', 'notes', 'Asked about FIU cybersecurity coursework'),
        -- dated relative to today so the dashboard always shows an upcoming interview
        JSON_OBJECT('date', DATE_FORMAT(CURDATE() + INTERVAL 7 DAY, '%Y-%m-%d'),
                    'round', 'Technical', 'interviewer', 'Security Team', 'notes', 'Review incident response and networking')
    )),
(2, '2026-09-18', 'Screening', 'v3-software', FALSE, JSON_ARRAY()),
(3, '2026-10-12', 'Applied',   'v3-security', TRUE,  JSON_ARRAY()),
(4, '2026-10-07', 'Rejected',  'v2-security', FALSE, JSON_ARRAY()),
(5, '2026-10-22', 'Applied',   'v3-security', TRUE,  JSON_ARRAY());

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'NextEra Recruiting',       'University Recruiting', NULL, NULL, NULL, 'Replace with a real contact'),
(3, 'Capital One Campus Team',  'Campus Recruiting',     NULL, NULL, NULL, 'Replace with a real contact'),
(4, 'CrowdStrike Talent Team',  'Talent Acquisition',    NULL, NULL, NULL, 'Replace with a real contact');