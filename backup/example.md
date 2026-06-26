# Example Document

This example demonstrates a Mermaid flowchart and a Gantt chart (Mermaid syntax).

## Flowchart

```mermaid
flowchart LR
  A[Start] --> B{Is it working?}
  B -- Yes --> C[Great]
  B -- No --> D[Fix it]
  D --> B
```

## Gantt

```mermaid
gantt
    title A Gantt Diagram
    dateFormat  YYYY-MM-DD
    section Planning
    Spec       :a1, 2024-01-01, 30d
    section Development
    Build      :after a1, 90d
    Test       : 2024-05-01, 30d
```

Regular markdown content, tables, lists, and code blocks are supported.
