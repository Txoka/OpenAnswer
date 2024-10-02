# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./

# Install dependencies and build
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Deploy
FROM node:18-alpine AS deploy

WORKDIR /app
COPY --from=builder /app/build /app/build

CMD ["npx", "serve", "-s", "build", "-l", "3000"]
