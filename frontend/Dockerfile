# Stage 1: Build
FROM node:19-alpine AS builder

WORKDIR /app
COPY . .

RUN npm install
RUN npm run build

# Stage 2: Deploy
FROM node:19-alpine AS deploy

WORKDIR /app
RUN npm install -g serve@13.0.2

COPY --from=builder /app/build /app/build

CMD ["npx", "serve", "-s", "build", "-l", "3000"]
