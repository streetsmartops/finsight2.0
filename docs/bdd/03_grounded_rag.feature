Feature: Grounded conversational answers (RAG layer)
  As an executive who will repeat the answer to a board
  I want every number in an answer to trace back to an engine computation
  So that I can trust it without checking a dashboard

  Background:
    Given a corpus of fact cards built from Capacity-Mngt-App and Cost-Mngt-App outputs
    And the TF-IDF retriever with a relevance floor of 0.04

  Scenario: A forward-risk question leads with the CRITICAL stream
    When I ask "Are we at risk of running out of capacity?"
    Then the retriever detects risk intent
    And boosts CRITICAL facts by 0.30
    And the top-2 evidence includes "Assist" and "CRITICAL"
    And the answer recommends a capacity action
    # test_rag_surfaces_critical_first_for_risk_queries

  Scenario Outline: Every citation exists in the corpus
    When I ask "<question>"
    Then the answer cites at least one FACT id
    And every cited FACT id exists in the corpus
    Examples:
      | question                                   |
      | Will we run out of capacity next quarter?  |
      | Why did our cloud spend spike?             |
      | What is our annualized spend?              |
    # test_rag_answers_are_grounded

  Scenario: Naming a dimension narrows the evidence
    When I ask "What happened with RDS in eu-west-1?"
    Then facts whose metadata matches "RDS" and "eu-west-1" are boosted by 0.15 each
    And the answer describes the orphaned read-replica incident

  Scenario: Off-domain questions are declined, not hallucinated
    When I ask "What is the airspeed velocity of an unladen swallow?"
    Then no fact clears the relevance floor
    And the evidence is empty
    And the answer says "I don't have a grounded fact"
    And no FACT ids are cited
    # test_rag_declines_when_no_facts

  Scenario: Fluent mode with a key, safe mode without
    Given ANTHROPIC_API_KEY is <key_state>
    When I ask an in-domain question
    Then the answer is composed by <composer>
    And used_llm is <used_llm>
    Examples:
      | key_state                | composer                         | used_llm |
      | set                      | Claude with the grounding prompt | true     |
      | unset                    | the deterministic template       | false    |
      | set but the call fails   | the template with a note         | false    |
