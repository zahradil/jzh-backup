
jzh-backup
=====================================

Names: jzhb, jzhbck

Utility for managing backups and snapshots created via hard-links.

App manages efficiently directory structure of hard-link created
backups of original data location. You can make backups every few hours,
but app will ensure that older backups are pruned, so you will still have
manageable amount of backups.

\b
Policy: - last 7 days - leave all untouched
 then: - leave 1 per day for 30 days
 then: - leave 1 per week for 4 weeks
 then: - leave 1 per month for 12 months
