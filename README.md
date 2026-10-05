# Climb.AI

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white&style=for-the-badge)
![Next.js](https://img.shields.io/badge/Next.js-000000?logo=next.js&logoColor=white&style=for-the-badge)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white&style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white&style=for-the-badge)

## About

**Climb.AI** is an AI-powered bouldering beta solver that analyzes indoor boulder problems from photos and generates personalized climbing sequences. Built with **FastAPI** and a custom computer vision pipeline using **Claude Vision AI**, it detects hold types, constructs a biomechanical route graph, simulates physics, and produces 8 distinct beta types tailored to each climber's profile.

## Features

- Claude Vision AI detects 24 hold types from 1–10 uploaded photos with normalized coordinates and confidence scores
- Biomechanics engine with 33 move types validated against 30+ climber anthropometric fields including height, ape index, shoulder mobility, and finger strength
- Physics simulation covering Coulomb friction, deadpoint/dyno momentum equations, and center-of-mass balance
- 8 generated beta types: high percentage, energy efficient, static, dynamic, heel-hook, toe-hook, compression, and coordination
- Difficulty analysis estimating V-grade and Fontainebleau grade with intensity breakdowns across power, finger, core, and coordination
- Interactive zoomable canvas with color-coded holds, active limb positions, and CoM indicator
- Persistent climber profiles that influence which moves are generated per analysis

## Technology Stack

- **Frontend**: Next.js, TypeScript, TanStack React Query, Zustand
- **Backend**: Python, FastAPI, Pydantic v2
- **AI**: Anthropic Claude Vision API
- **Infrastructure**: Docker Compose

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set up environment:
   ```bash
   cp .env.example .env.local
   ```

3. Run locally:
   ```bash
   npm run dev
   ```

4. Open http://localhost:3000

## How It Works

Upload a climbing problem image. The app analyzes the image using Claude Vision AI to identify holds and movements, then provides beta (solution hints).

## Tech Stack

- Next.js 16
- TypeScript
- Claude Vision API
- Tailwind CSS
