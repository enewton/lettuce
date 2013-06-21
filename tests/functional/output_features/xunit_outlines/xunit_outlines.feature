Feature: Test XML output matches console for Skipped steps

  Scenario: Scenario with undefined step
    Given this test step passes
    When this test step is undefined

  Scenario Outline: Outline scenario with general undefined step
    Given the mode is squared
    And this step is undefined
    When the input is set to <in>
    Then the output is <out>

  Examples:
  | in | out |
  |  1 |  1  |
  |  2 |  4  |

  Scenario Outline: Outline scenario with 1st eg undefined step
    Given the mode is squared
    When the input is set to <in>
    Then the output is <out>

  Examples:
  | in |    out    |
  |  1 | undefined |
  |  2 |     4     |

  Scenario Outline: Outline scenario with last eg undefined step
    Given the mode is squared
    When the input is set to <in>
    Then the output is <out>

  Examples:
  | in |    out    |
  |  1 |     1     |
  |  2 | undefined |
