FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

EXPOSE 3000

# host 0.0.0.0 is required so Docker can expose the port outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
