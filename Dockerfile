FROM node:22-alpine
WORKDIR /app
COPY relay/server.js ./server.js
ENV PORT=8787
EXPOSE 8787
CMD ["node","server.js"]
