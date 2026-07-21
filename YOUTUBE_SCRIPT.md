# MetisOne Platform YouTube Script

## 1. Opening

Hi everyone, my name is Scott, and today I want to show you MetisOne Platform.

I have worked in the BI industry for many years. Over time, I noticed one big problem: most BI tools are powerful, but they are also too complex.

There are too many settings, too many screens, and too many features that most users never use.

In many companies, users may only need 20 to 30 percent of the product. But the company still has to pay for the whole package.

Now, with AI agents, I think we have a chance to make BI much simpler.

Instead of asking users to configure every model, metric, filter, and query by hand, MetisOne lets users work with data through chat.

Users can build the semantic layer with natural language. They can edit semantic models through chat. And they can ask complex data questions through chat.

The goal is simple: make BI easier to use, faster to set up, and more focused on what customers actually need.

## 2. The Problem With Traditional BI

Before we go deeper, let me quickly explain what BI means to me.

I like to describe BI with three "rights":

Show the right data, to the right person, in the right way.

That sounds simple. But most BI products have become bigger and bigger over time.

To support different companies, different teams, and different use cases, they keep adding more and more features.

After a while, the product becomes very powerful, but also very hard to learn.

Have you seen configuration screens like these?

Here, I can show some examples from tools like Power BI, Tabular Editor, or MicroStrategy.

For experienced BI engineers, these screens may be okay. But for many business users, analysts, and small teams, they can feel overwhelming.

Sometimes it feels like this: you start as a beginner, you open the configuration page, and then you almost want to give up.

Based on my experience, maybe 70 percent of BI features are rarely used. Another 15 percent may only be used once a month, or once a quarter.

But the company still pays for all of it.

At one of my previous companies, we had almost 20 different types of filters. Many of them were very similar. They existed because different enterprise customers needed slightly different custom behavior.

That flexibility can be useful for large companies. But it also makes the system harder to learn, harder to maintain, and more expensive for everyone else.

This is the gap I want MetisOne to address.

## 3. What MetisOne Does Differently

MetisOne takes a different approach.

I want to build a simple and easy-to-use BI platform that can meet the needs of small and mid-sized businesses. It should also be easy to integrate into a customer's existing system.

Based on the three "rights" idea, we can break a BI system into three major parts.

The right data means data querying.

The right person means security.

The right way means presentation.

In this project, I leave security to the customer system for now. MetisOne focuses on data querying and presentation.

In this video, I will focus on data querying. I will show you how to build a simple but powerful data query system with AI.

MetisOne is built on top of Cube Core. If you are interested in Cube, you can visit the Cube website and learn more about it. Cube is a very strong open-source product. It provides a semantic layer and a query engine.

On top of Cube Core, MetisOne adds an AI agent layer.

This AI layer helps users create and update semantic model elements, such as dimensions, measures, and joins. It also helps users query data.

And the whole process can happen through chat and natural language, instead of complex configuration pages.

## 4. Demo Setup

Now let me show you a quick demo.

In my environment, I have a PostgreSQL database with a sample DVD rental database. I also have Cube Core running in a virtual machine.

If you want to install and set up Cube Core with your own database, you can check the official Cube documentation.

First, I open the Cube Core configuration page.

Here, Cube is connected to the PostgreSQL database.

You can see a list of database tables and views.

For this demo, I select the tables and let Cube generate the initial semantic model.

This is a good starting point. Cube can generate basic cubes, dimensions, and measures from the database schema.

But the generated model is not always complete.

For example, some tables may need a primary key. Some relationships may need join definitions. And some business metrics may need extra semantic logic.

In MetisOne, I use a Semantic Edit Service to update and complete this model.

Instead of opening the YAML file and editing everything by hand, I can send a request through the chat UI.

For example, I can say:

"Add a full name dimension to actor, based on first name and last name."

The AI agent understands the request, finds the right cube, creates the right dimension, and updates the semantic model.

So the user does not need to remember the YAML syntax. They can describe what they want.

## 5. Data Querying With Chat

The second part is data querying.

After the semantic model is ready, users can ask business questions directly.

For example:

"How many films are there?"

Or:

"How many Action films are there?"

MetisOne sends the question to an AI planner. The planner reads Cube metadata, creates a Cube REST query, validates it, runs it through Cube, and returns the result.

So instead of writing SQL, or manually building a report, the user can start with a simple question.

MetisOne turns that question into a structured query and gives back structured data.

## 6. Closing

This is still an early version of MetisOne, but the direction is clear.

I want to keep the power of a semantic BI platform, but make the user experience much simpler.

AI should not replace the semantic layer. It should make the semantic layer easier to build, easier to understand, and easier to use.

That is the main idea behind MetisOne Platform.

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
