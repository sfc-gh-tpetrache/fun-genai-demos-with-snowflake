use role accountadmin;
create database tarot_ai;
create stage tarot_cards
  DIRECTORY = (enable = true)
  ENCRYPTION = (type = 'snowflake_sse');

  