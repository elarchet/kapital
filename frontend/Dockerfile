# Build stage
FROM node:22-alpine AS build-stage

WORKDIR /app

# Copy package configurations
COPY package*.json ./

# Install packages
RUN npm ci

# Copy all code files
COPY . .

# Build the Vite application
RUN npm run build

# Final production stage with Nginx
FROM nginx:1.27-alpine AS production-stage

# Copy built assets
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy routing rules
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
