FROM node:16-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Set environment variable to fix the crypto issue
ENV NODE_OPTIONS=--openssl-legacy-provider

CMD ["npm", "start"]