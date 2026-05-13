function [EUBED] = f_EUBED(Phantom,BED,organo,alfa)


ind=Phantom==organo;

BED1=BED(ind);
n=length(BED1);

EUBED=-alfa.*BED1;
EUBED=exp(EUBED);
EUBED=sum(EUBED)/n;
EUBED=log(EUBED);
EUBED=-EUBED/alfa;

end

