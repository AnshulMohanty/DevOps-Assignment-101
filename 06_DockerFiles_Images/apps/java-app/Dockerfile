# Stage 1: compile with the full JDK
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /src
COPY App.java ./
RUN javac App.java

# Stage 2: run on the much smaller JRE
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /src/App.class ./
EXPOSE 8080
CMD ["java", "App"]
