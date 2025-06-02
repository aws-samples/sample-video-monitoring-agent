# Use Amazon Linux 2 base image
FROM amazonlinux:2

# Install necessary packages
RUN yum update -y && yum install -y \
    ffmpeg \
    python3 \
    && yum clean all \
    && rm -rf /var/cache/yum

# Set the working directory
WORKDIR /app

# Copy the script to process and serve the video
COPY run.sh /app/

# Make the script executable
RUN chmod +x /app/run.sh

# Expose the port the server will run on
EXPOSE 8080

# Run the script when the container starts
CMD ["/app/run.sh"]
