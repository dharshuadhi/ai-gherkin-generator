Feature: User login
  As a registered user
  I want to log in with my email and password
  So that I can access my account securely

  Background:
    Given a "registered user" is using the system

  Scenario: AC1 - the user submits valid credentials, then they are taken to the dashboard
    Given a "registered user" is using the system
    When the user submits valid credentials
    Then they are taken to the dashboard

  Scenario: AC2 - the user submits an invalid password 3 times, then the account is temporarily locked
    Given a "registered user" is using the system
    When the user submits an invalid password 3 times
    Then the account is temporarily locked

  Scenario: AC3 - An error is shown when the email format is invalid
    Given a "registered user" is using the system
    When the registered user tries to log in with their email and password
    Then an error is shown when the email format is invalid

  Scenario: AC4 - Sessions expire after 30 minutes of inactivity
    Given a "registered user" is using the system
    When the registered user tries to log in with their email and password
    Then sessions expire after 30 minutes of inactivity

  Scenario: Validation - invalid input is rejected
    Given a "registered user" is using the system
    When the user submits invalid input
    Then a clear validation error is displayed
    And no data is saved
