# FlightWise AI

Sure. Here's a short, high-impact prompt you can paste into an AI website builder:

Build a premium, interactive aviation AI web app called FLITZZZZ, an AI-powered flight delay prediction and operational intelligence platform. Use an Apple-inspired minimalist design with elegant animations, large typography, generous whitespace, and a professional aviation aesthetic. Support both Dark and Light themes with a smooth theme toggle and persist the user's preference.

Landing page: cinematic full-screen hero with animated aircraft flying along a glowing route/map, headline "Know the risk. Before the delay.", subtext about AI flight-delay prediction, and CTAs "Predict a Flight"and "Explore Dashboard". Add scroll-based storytelling showing flight signals such as time, airport, traffic, weather, and historical patterns converging into a delay-risk prediction.

Loading screen: show the FLITZZZZ logo and a small animated aircraft flying across a route while loading flight data, airport network, and prediction engine.

Pages: Landing, Login, Dashboard, Flights, Predict, Insights, Model Performance, and Reports.

Dashboard: KPI cards for flights analyzed, high-risk flights, delay rate, and model AUC; interactive flight/airport map with animated aircraft routes; high-risk flight table.

Predict page: interactive input form for airline, origin, destination, date, departure time, scheduled arrival, distance, weather, and traffic intensity. On prediction, animate the aircraft and show an animated delay probability, Low/Medium/High risk, contributing factors/SHAP explanation, operational context, and interactive route map.

Map: display origin/destination airports, animated flight path, airport markers, and latitude/longitude from the airport dataset.

Insights: interactive charts for airport delay rates, departure-hour patterns, monthly/seasonal trends, routes, traffic intensity, and weather.

Model page: AUC-ROC, precision, recall, F1, ROC curve, confusion matrix, model comparison, and feature importance.

Reports: generate a polished flight-risk report containing flight details, probability, risk level, contributing factors, map, coordinates, model information, and timestamp, with Download PDF / Print options.

Visual style: Manrope for headings, Inter for UI/body, dark navy + electric blue in dark mode, white + blue in light mode, red/amber/green only for risk levels. Use subtle glass effects, smooth transitions, hover interactions, responsive design, accessible contrast, and reduced-motion support. Make it feel like a real premium aviation SaaS product, not a generic ML dashboard.

Core message: FLITZZZZ — Predict. Explain. Act. ✈️

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/f3a7d8f0-4952-4909-a31e-7c4b3942693f).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
