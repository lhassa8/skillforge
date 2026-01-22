---
schema_version: "1.0"
name: data-analyst
description: Use when asked to analyze data, create visualizations, or generate insights from datasets. Supports CSV, JSON, and tabular data.
version: 2.1.0
min_skillforge_version: 1.0.0
author: SkillForge Examples
license: MIT
tags:
  - data
  - analysis
  - visualization
---

# Data Analyst

Help users analyze data, identify patterns, and generate actionable insights.

## Capabilities

- **Data Exploration**: Summarize structure, types, missing values
- **Statistical Analysis**: Descriptive stats, correlations, distributions
- **Pattern Detection**: Trends, anomalies, clusters
- **Visualization Suggestions**: Recommend appropriate chart types
- **Insight Generation**: Actionable conclusions from data

## Analysis Framework

### Step 1: Understand the Data

```
- What is the data about?
- How many rows/columns?
- What are the data types?
- Any missing or invalid values?
```

### Step 2: Explore Distributions

```
- Numerical: mean, median, std, min, max, quartiles
- Categorical: unique values, frequencies
- Temporal: date ranges, seasonality
```

### Step 3: Find Relationships

```
- Correlations between numerical columns
- Group comparisons
- Time-based trends
```

### Step 4: Generate Insights

```
- Key findings (with evidence)
- Anomalies or concerns
- Recommended actions
- Further questions to explore
```

## Examples

### Example 1: Sales Data Analysis

**User**: Analyze this sales data:
```csv
date,product,region,sales,units
2024-01-01,Widget A,North,1500,30
2024-01-01,Widget B,South,2300,45
2024-01-02,Widget A,North,1800,35
...
```

**Response**:

## Data Overview

- **Records**: 1,000 rows
- **Columns**: 5 (date, product, region, sales, units)
- **Date Range**: Jan 1 - Dec 31, 2024
- **Missing Values**: None

## Key Statistics

| Metric | Sales ($) | Units |
|--------|-----------|-------|
| Mean | 2,150 | 42 |
| Median | 1,950 | 38 |
| Std Dev | 850 | 15 |
| Min | 500 | 10 |
| Max | 5,200 | 95 |

## Key Insights

1. **Regional Performance**: North region outperforms South by 23% in average sales
2. **Product Trend**: Widget B shows 15% month-over-month growth
3. **Seasonality**: Q4 sales are 40% higher than Q1
4. **Anomaly**: Unusual spike on March 15 (investigate promotion?)

## Recommended Visualizations

1. Line chart: Sales over time by region
2. Bar chart: Product comparison by region
3. Heatmap: Sales by day of week and hour

## Recommended Actions

1. Investigate North region success factors
2. Increase Widget B inventory for Q4
3. Plan promotions for Q1 to balance seasonality

### Example 2: Quick Summary

**User**: What's the average and distribution?

**Response**:

If you share your data, I'll provide:
- Mean, median, mode
- Standard deviation and variance
- Min, max, and range
- Quartiles (25th, 50th, 75th percentiles)
- Distribution shape (normal, skewed, bimodal)

Please paste your data or describe what you're analyzing.
