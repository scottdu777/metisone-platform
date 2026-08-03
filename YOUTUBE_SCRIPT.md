# MetisOne Platform YouTube Script

## 1. Opening and Introduction

Hi everyone, my name is Scott.

Today I want to show you a BI platform I am building. It is called MetisOne.

MetisOne AI Platform is a BI platform built on top of Cube Core. It extends
Cube Core's semantic layer with AI-assisted model editing and natural-language
data querying. Users can build and refine semantic data models through chat,
then ask complex analytical questions through chat and get result.

2. Cube core is an open-source engine for semantic layers and data queries. Cube Core gives us a strong foundation for defining dimensions, metrics, joins, and reusable business logic. If you want to learn more about Cube Core, you can visit their official website at https://cube.dev/.

3. Why the semantic layer is so important to BI.

Becuase without a semantic layer, the AI has to deal directly with database tables, column names, joins, and SQL logic. That is risky, because business data always is complicated. 

A semantic layer gives raw data business meaning. It defines metrics, dimensions, joins, and reusable business logic in a consistent way.

So when a user asks a question in plain English, the AI does not have to guess from raw tables. It can work through the semantic layer and return a more reliable answer.

in short, a semantic layer is the bridge between raw data and business language.


4. My system has four main parts.

First, there is Cube Core. This is the open-source product from Cube Dev. It manages the semantic layer and executes data queries.

Second, I added a Semantic Layer Edit Service.
Cube Core is a great semantic layer engine, but its support for model editing is still limited. For example, it is not easy to add new dimensions through an API, and the auto-generated models may miss important information such as primary keys or joins.
So I built this Edit Service to enhance model editing by directly updating the Cube YAML models. It can manage dimensions, metrics, joins, primary keys, and other semantic model definitions.

Third, there is a Data Query Service. This service takes a natural language question, uses the semantic layer metadata, and turns the question into a Cube REST query that Cube Core can execute.

Finally, there is the client application. This is the chat UI. It is the main entry point for users. From this interface, users can manage the data model and query data through conversation.

So the idea is simple: use Cube Core as the reliable semantic layer and query engine, and use AI agents to make the whole BI workflow easier to use.

Now, let's jump into the demo.













The reason I started this project is also pretty simple.

I have worked in the BI industry for many years, and I noticed one common problem.

Most BI products are very powerful, but they are also too complex. They come with a lot of features, a lot of configuration options, and a lot of screens.

But in real projects, each customer may only use 20 or 30 percent of the product. The rest is rarely used.

The problem is, customers still have to learn it, manage it, and pay for it.

Why does this happen?

Because every customer has slightly different needs.

For example, one customer may want charts with rounded corners, while another customer wants square corners.

One customer may only need a simple filter for dimensions and metrics. Another customer may want a complex filter builder with many conditions.

So what do BI companies usually do?

They keep adding more.

More options. More screens. More special logic. More custom settings.

That is feature creep.

At one of my previous companies, we had almost 20 different types of filters and three different types of dashboards.

Many of them were doing almost the same job.

That felt wrong to me.

So I started asking myself:

Can we make BI simpler for small and mid-sized companies?

Can we give them the core features they actually need, with less configuration, a better user experience, and a lower cost?

Now that we have AI agents, I think the answer is yes.

We can let AI handle a lot of the complex configuration work dynamically, while users focus on what they actually want from the data.

And that is why I started building MetisOne.
## 2. What BI Means To Me

Before I jump into the demo, let me explain how I think about BI.

For me, BI is really about three things.

Show the right data, to the right person, in the right way.

That is it.

The right data means we can find the correct data and return the correct answer.

The right person means security. A user should only see the data they are allowed to see.

The right way means presentation. Sometimes the answer should be a Grid table. Sometimes it should be a chart. Sometimes it should be a dashboard or a report.


Many BI companies are beginning to adopt an AI-first approach. They allow users to get information through chat, while reducing the need to manually create charts or retrieve data.

For example:

"Show me revenue by month."

That feels much more natural than clicking through ten different setup screens.

But there is one important piece behind this: the semantic layer.

Without a semantic layer, the AI has to deal directly with database tables, column names, joins, and SQL logic. That is risky, because business data is rarely simple.

For example, two teams may both talk about revenue, but one team may include refunds, and another team may not. If those definitions are not managed in one place, the same question can produce different answers.

A semantic layer solves this problem. It gives raw data business meaning. It defines metrics, dimensions, joins, and reusable business logic in a consistent way.

So when a user asks a question in plain English, the AI does not have to guess from raw tables. It can work through the semantic layer and return a more reliable answer.

However, complex databases still require a strong semantic layer. New dimensions and metrics often need to be designed before users can query them correctly, and that usually requires knowledge of the database schema.

So the next question is:

Can that work also be done through chat?

## 3. What MetisOne Does Differently

So MetisOne is my attempt to build that kind of BI system.

I am not trying to build a giant enterprise BI suite with every possible feature.

That is not the goal.

My goal is to build something simpler and easier to understand.

Something that can cover the common BI needs of small and mid-sized companies.

And if a company needs more, the system should be modular, so developers can extend it.

In this video, I am mainly focusing on one part:

Data querying.

MetisOne is built on top of Cube Core.

Cube Core already gives us a semantic layer and a query engine.

That is important because the semantic layer gives business meaning to raw data.

Without a semantic layer, users need to understand database tables, joins, and SQL.

Different teams may also calculate the same metric, such as revenue, in different ways.

A semantic layer gives us consistent definitions for metrics and dimensions.

It defines the correct relationships between data tables.

It lets us reuse business logic.

It also gives BI tools and AI agents a simpler interface to work with.

And most importantly, it helps the system return more reliable and trustworthy answers.

In simple terms, the semantic layer is a bridge between complex database structures and the language business users understand.

That is a very strong foundation.

On top of that, MetisOne adds an AI agent layer.

This layer improves how users manage the semantic layer and how they query data through Cube Core.

## 4. Demo Setup

Now let me show you the demo setup.

I am using a PostgreSQL database with a sample DVD rental dataset.

I also have Cube Core running in a virtual machine.

First, I open Cube Core.

Cube is connected to my PostgreSQL database.

Here we can see the database tables and views.

For this demo, I select the tables and let Cube generate the first version of the semantic model.

This is a good start.

Cube can read the database schema and generate basic cubes, dimensions, and measures.

But the generated model is not perfect.

Some tables may be missing primary keys.

Some joins may need to be added.

Some business logic may need to be defined manually.

In a traditional setup, I would open the YAML files and edit them by hand.

That works, but it is not very friendly.

In MetisOne, I use a Semantic Edit Service.

The edit service can update the Cube YAML model through an API.

And on my local machine, I have a chat UI with an AI agent.

So I can type something like:

"Add a full name dimension to actor, based on first name and last name."

The agent figures out which cube to use, what field to create, and how to update the model.

The user does not need to remember the YAML syntax.

They just describe the change they want.

## 5. Data Querying With Chat

The next part is querying data.

Once the semantic model is ready, the user can ask questions directly.

For example:

"How many films are there?"

Or:

"How many Action movies are there?"

MetisOne sends that question to an AI planner.

The planner looks at the Cube metadata and builds a Cube REST query.

Then MetisOne validates the query, sends it to Cube, gets the result back, and returns a simple answer.

So the user does not need to write SQL.

They do not need to build a report first.

They can start with a question.

And behind the scenes, MetisOne turns that question into a structured Cube query.

## 6. Closing

This project is still early.

There is a lot more to build.

But the direction is pretty clear to me.

I do not think AI should replace the semantic layer.

The semantic layer is still very important.

It gives the system structure, definitions, and trust.

But AI can make the semantic layer much easier to build and much easier to use.

That is the idea behind MetisOne.

Keep the power of BI.

Remove as much complexity as possible.

And let users work through natural language when it makes sense.

Thanks for watching.

## Suggested Video Flow

1. Opening: why I built MetisOne
2. Problem: traditional BI is too complex
3. Concept: the three rights of BI
4. Architecture: Cube Core plus MetisOne AI agent layer
5. Demo: generate Cube semantic model
6. Demo: edit semantic model through chat
7. Demo: query data through chat
8. Closing: future vision
