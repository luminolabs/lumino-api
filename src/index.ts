import express from 'express';
import http from 'http';
import bodyParser from 'body-parser';
import cookieParser from 'cookie-parser';
import compression from 'compression';
import cors from 'cors';
import mongoose from 'mongoose';

import router from './router';
import * as dotenv from 'dotenv';
dotenv.config();

const app = express();

app.use(cors({
    credentials: true,
}));

app.use(compression());
app.use(cookieParser());
app.use(bodyParser.json());

const server = http.createServer(app);

server.listen(8080, () => {
    console.log('Server is running on http://localhost:8080/');
});

const MONGO_URL = 'mongodb+srv://yogesh:LD4pDHmDqBre1M6j@lumino-data.70dgucp.mongodb.net/?retryWrites=true&w=majority';
//const MONGO_URL = `mongodb+srv://yogesh:${process.env.MONGO_DB_PASSWORD}@decompute.r0klqyg.mongodb.net/?retryWrites=true&w=majority`

mongoose.Promise = Promise;
mongoose.connect(MONGO_URL);
mongoose.connection.on('error', (error: Error) => console.log(error))
console.log('connected!')

app.use('/', router());