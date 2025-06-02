# Build
```shell
docker build -t hls-server .
```
# Run instructions
```shell
docker run -it -p 8080:8080 -v /path/to/your/video.mkv:/input.mkv -e INPUT_FILE=/input.mkv hls-server
```
You can then access your HLS stream at http://localhost:8080/playlist.m3u8.