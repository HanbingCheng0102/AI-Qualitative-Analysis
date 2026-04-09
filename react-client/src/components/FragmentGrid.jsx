import { useAtom } from "jotai";
import FragmentGridIcon from "./FragmentGridIcon";
import { fragments } from "../state";

function FragmentGrid({subsetList, selectedFragment, setSelectedFragment}){

    return(
        <ul className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 p-1 content-start">
            {subsetList.map((item, index) => (
                <li key={item._id}>
                <FragmentGridIcon fragment={item} selectedFragment={selectedFragment} setSelectedFragment={setSelectedFragment}></FragmentGridIcon>
                </li>
            ))}
        </ul>
    )
}

export default FragmentGrid