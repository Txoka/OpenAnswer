# Stage 1: Build
FROM node:19-alpine AS builder

WORKDIR /app
COPY . .

RUN npm install
RUN npm run build && test -d /app/build

# Stage 2: Deploy
FROM node:19-alpine AS deploy

WORKDIR /app
COPY --from=builder /app/build /app/build

CMD ["npx", "serve", "-s", "build", "-l", "3000"]
