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













Now I want to talk about why I started this project.

I have worked in the BI industry for many years, and I noticed one common problem.

Many BI systems look very powerful, but most users use less than 30 percent of the features, while still paying for 100 percent of the product.

And customers often have special requests.

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

Can we use AI agents to handle much of this configuration work?

At the end of the day, most BI systems still need to generate SQL or query requests to get data from the database.

If an AI agent can understand the user's request, work with the semantic layer, and generate the right query, then we can remove many complicated configuration screens.

The agent can create the query dynamically based on what the user asks for. That means the system can support many special customer needs without adding a new feature for every small variation.

Right now, this application is still an early proof of concept.

The main goal is to test whether this idea can really work.

There are still many things to improve, such as generating more accurate query requests, reducing token usage, and adding better chart visualization on the front end.

I will keep improving it over time.

If you like this idea, or if you have any suggestions, please leave a comment. Thank you for watching.
