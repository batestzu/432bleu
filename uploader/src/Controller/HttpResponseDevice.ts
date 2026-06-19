import {Readable} from "stream";
import {Response} from "express";
import {mimeTypeManager} from "../Service/MimeType";
import {TargetDevice} from "../Service/TargetDevice";

export class HttpResponseDevice implements TargetDevice {
    constructor(private id: string, private response: Response) {
    }

    copyFromLink(link: string): void {
        this.response.redirect(link);
    }

    copyFromBuffer(buffer: Buffer | undefined | null): void {
        if (buffer == undefined) {
            this.response.status(404).send("Cannot find file");
            return;
        }

        this.response.status(200);
        this.response.setHeader("Content-Disposition", `attachment; filename="${encodeURIComponent(this.id)}"`);
        this.response.setHeader("X-Content-Type-Options", "nosniff");

        const mimeType = mimeTypeManager.getMimeTypeByFileName(this.id);
        this.response.type(mimeType !== false ? mimeType : "application/octet-stream");

        this.response.send(buffer);
    }
}
