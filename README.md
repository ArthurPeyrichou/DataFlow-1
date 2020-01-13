# DataFlow

DataFlow is a web service for data processing. It allows to use component oriented processing based on the wonderful [Total.js flow](https://github.com/totaljs/flow) app. The backend is changed to python to take advantage of python libraries. These components are stored in [another repository](https://github.com/Rarioty/DataFlow-Components).

## Installation

The webservice is separated in two services (frontend and backend) handled with Docker images. The whole package can be launched with the provided docker-compose file.

```bash
docker-compose up -d
```

## Configuration

The default configuration will launch the webservice on the ports 8000 and 5001 for websocket and will allow the access only from localhost. You can configure the service by modifying the config file in frontend service:

```
name                         : DataFlow

// Packages settings
package#flow       (Object)  : { url: '/', type: 'client', external: 'ws\\://{SERVICE DOMAIN}\\:{WEBSOCKET PORT}' }
```

You have to change the {SERVICE_DOMAIN} with the domain name or ip of your backend and the port accordingly. Make sure to be in sync with the docker-compose file.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## Thanks

As this work is based a lot on the app from [Total.js](https://github.com/totaljs), make sure to go see their work and drop a star :)

## License
[MIT](LICENSE)