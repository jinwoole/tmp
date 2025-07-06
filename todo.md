# Load Balancer Visualization App - TODO

## 작업 계획

- [x] **애니메이션 순서 오류 수정:** 클라이언트와 로드밸런서에서 동시에 출발하는 신호를 클라이언트 -> 로드밸런서 -> 서버 순서로 변경. (`NetworkCanvas.svelte`)
- [x] **탄두 궤적 수정:** 곡선 궤적을 직선으로 변경. (`ElectricityEffect.js`)
- [x] **탄두 속도 증가:** 탄두의 이동 속도를 높임. (`ElectricityEffect.js`)
- [x] **탄두 색상 변경:** 탄두 색상을 파란색으로 변경. (`ElectricityEffect.js`)

## 변경 사항 요약 (Review)

- **`src/lib/animation/ElectricityEffect.js`**
  - `createEffect` 함수를 수정하여 파티클(탄두)의 궤적을 `quadraticCurveTo`를 사용한 곡선에서 선형 보간을 사용한 직선으로 변경했습니다.
  - 파티클의 색상을 주황색(`0xFF9500`)에서 파란색(`0x00BFFF`)으로 변경하고, 크기를 약간 키웠습니다.
  - 애니메이션 `duration`을 `0.5`초에서 `0.25`초로 줄여 속도를 높였습니다.

- **`src/lib/components/NetworkCanvas.svelte`**
  - 이벤트 발생 시 애니메이션을 생성하는 로직을 수정했습니다.
  - `setTimeout`을 사용하여 '클라이언트 -> 로드 밸런서' 애니메이션이 끝난 후 '로드 밸런서 -> VM' 애니메이션이 순차적으로 실행되도록 변경하여 동시 출발 문제를 해결했습니다.
  - 파티클 효과 또한 각 신호가 노드에 도달하는 시점에 맞춰 발생하도록 조정했습니다.

This file tracks the tasks for creating the real-time load balancer visualization application.

## Plan

# Design Overhaul: Apple-Inspired Aesthetic

This file tracks the tasks for redesigning the application to have a clean, modern, and minimal aesthetic, similar to Apple's design language.

## Plan

- [x] **1. Adjust Visualization Layout**
  - [x] Modified `NodeManager.js` to increase the spacing between VM nodes, preventing them from overlapping.

- [x] **2. Update Color Palette**
  - [x] Changed the primary accent color to a vibrant orange.
  - [x] Updated `ElectricityEffect.js` and `ParticleSystem.js` to use the new orange color.
  - [x] Replaced the cyberpunk-style glows and shadows with a more subtle and clean look.

- [x] **3. Refine UI Components**
  - [x] Updated `+page.svelte` to use a cleaner font, a modern dark background, and removed text shadows.
  - [x] Redesigned `StatsPanel.svelte` with the new color scheme, improved spacing, and cleaner borders.

- [x] **4. Final Review**
  - [x] Tested the application to ensure all design changes are applied correctly.
  - [x] Confirmed the visualization is clear and aesthetically pleasing.

## Review

The application's design has been completely overhauled to align with a clean, modern, and minimal aesthetic inspired by Apple's design language.

- **Visual Clarity:** The visualization layout was improved by increasing the spacing between VM nodes, preventing overlap and enhancing readability. Node labels now show their actual ID for better identification.
- **Cohesive Color Palette:** A new color scheme was implemented, featuring a sophisticated dark theme with a vibrant orange accent. This creates a professional and focused user experience.
- **Refined UI:** All UI components, including the main page and stats panel, were redesigned with improved typography, spacing, and a consistent visual style. The result is a polished and aesthetically pleasing interface that is easy to navigate and understand.

# Dockerization

This section outlines the plan to containerize the Svelte application using Docker.

## Plan

- [x] **1. Create Dockerfile**
  - [x] Set up a multi-stage build to create an optimized production image.
  - [x] Stage 1: Build the SvelteKit application.
  - [x] Stage 2: Create a minimal final image with the Node.js server.

- [x] **2. Create docker-compose.yml**
  - [x] Define a service to build and run the application.
  - [x] Use `network_mode: "host"` to allow the application to access the host's IP address directly.

- [x] **3. Final Review**
  - [x] Add a summary of the Docker setup to this file.

## Review

The application has been successfully containerized using Docker.

- **`Dockerfile`**: A multi-stage `Dockerfile` was created to build an optimized production image. It first builds the SvelteKit application and then copies only the necessary artifacts to a minimal Node.js base image, reducing the final image size.
- **`docker-compose.yml`**: A `docker-compose.yml` file was created to simplify the process of building and running the application. It uses `network_mode: "host"` to ensure that the SvelteKit backend can correctly determine the host's IP address, which was a key requirement.
