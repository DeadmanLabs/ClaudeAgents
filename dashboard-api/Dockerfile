FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Install Python for running the Python implementation
RUN apk add --update python3 python3-dev py3-pip

EXPOSE 3000

CMD ["npm", "run", "dev"]