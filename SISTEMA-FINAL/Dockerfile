# Build: docker build -f SISTEMA-FINAL/Dockerfile .
# Contexto deve ser a raiz FROTA/ (para incluir nginx/default.conf).

FROM node:20-alpine AS build

WORKDIR /app

COPY SISTEMA-FINAL/package.json SISTEMA-FINAL/package-lock.json ./
RUN npm ci

COPY SISTEMA-FINAL/ ./

ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
