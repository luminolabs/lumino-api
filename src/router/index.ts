import express from 'express';
import authentication from './authentication';
import users from './users';
import computeprovider from './computeprovider';

const router = express.Router();

export default (): express.Router => {
    authentication(router);
    users(router);
    computeprovider(router);
    return router;
};
