# comments-retriever
Project that read and store locally comment from some spanish newspaper

# Generate package
```
make package
```

# Generate docker
```
make docker version={version}
```

# Launch docker
```
docker run -it --rm -v /tmp:/results \ 
    -e BEGIN="15/10/2019" \
    -e END="17/10/2019" \ 
    -e MEDIA="abc" \
    -e RESULTS_PATH="/results" \
    scrapper:0.1.0 
```


